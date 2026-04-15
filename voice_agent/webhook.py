import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from property_agent.models import Property, Transcript
from .ai_engine import get_ai_response

logger = logging.getLogger(__name__)



# CONSTANTS


MAX_RESULTS_TO_AI   = 3     # max properties sent to Gemini
FILTER_THRESHOLD    = 20    # if DB returns more than this, ask to narrow down

CITY_LIST = [
    "chennai", "mumbai", "bangalore", "bengaluru", "pune",
    "delhi", "hyderabad", "kolkata", "ahmedabad", "surat",
    "jaipur", "lucknow", "noida", "gurugram", "gurgaon",
    "coimbatore", "madurai", "thane", "navi mumbai"
]

TYPE_MAP = {
    "1bhk"      : "1BHK",
    "2bhk"      : "2BHK",
    "3bhk"      : "3BHK",
    "4bhk"      : "4BHK",
    "5bhk"      : "5BHK",
    "studio"    : "Studio",
    "villa"     : "Villa",
    "penthouse" : "Penthouse",
    "plot"      : "Plot",
    "duplex"    : "Duplex",
    "bungalow"  : "Bungalow",
    "row house" : "Row House",
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def voice_response(text: str) -> JsonResponse:
    # Return a plain voice message to Vapi.
    return JsonResponse({"response": text})


def tool_response(tool_call_id: str, result: str) -> JsonResponse:
    # Return a properly formatted Vapi tool-call response.
    return JsonResponse({
        "results": [
            {
                "toolCallId": tool_call_id,
                "result": result
            }
        ]
    })


def extract_city(text: str, existing: str) -> str:
    #Extract city from raw text if not already provided by Vapi.
    if existing:
        return existing
    for city in CITY_LIST:
        if city in text:
            if city == "bengaluru":
                return "Bangalore"
            if city == "gurugram":
                return "Gurgaon"
            if city == "navi mumbai":
                return "Navi Mumbai"
            return city.title()
    return ""


def extract_property_type(text: str, existing: str) -> str:
    """Extract property type from raw text if not already provided by Vapi."""
    if existing:
        return existing
    for keyword, ptype in TYPE_MAP.items():
        if keyword in text:
            return ptype
    return ""


def build_property_context(properties) -> str:
    """
    Build a clean, clearly labeled key-value block per property
    so Gemini can easily extract any field the caller asks about.
    """
    blocks = []

    for p in properties:
        fields = {
            "Name"         : p.name or "N/A",
            "City"         : p.city or "N/A",
            "Property Type": p.property_type or "N/A",
            "Price"        : f"{p.price_in_lakhs} lakhs" if p.price_in_lakhs else "N/A",
            "Carpet Area"  : f"{p.carpet_area} sqft" if p.carpet_area else "N/A",
            "Bedrooms"     : f"{p.bedrooms} BHK" if p.bedrooms else "N/A",
            "Parking"      : "Available" if p.parking else "Not Available",
            "Amenities"    : p.amenities or "N/A",
            "Description"  : p.description or "N/A",
        }

        block = "\n".join(f"  {k}: {v}" for k, v in fields.items())
        blocks.append(f"Property:\n{block}")

    return "\n\n".join(blocks)


def save_transcript(property_obj, caller_query: str, ai_response: str):
    """Save a transcript entry safely."""
    try:
        Transcript.objects.create(
            property=property_obj,
            caller_query=caller_query,
            ai_response=ai_response
        )
    except Exception as e:
        logger.error(f"[TRANSCRIPT SAVE ERROR] {str(e)}")



# Webhook called by vapi , exposed
@csrf_exempt
def vapi_webhook(request):
    if request.method != "POST":
        return voice_response("Invalid request method.")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("[WEBHOOK] Invalid JSON received")
        return voice_response("Sorry, I couldn't understand the request.")

    message    = data.get("message", {})
    event_type = message.get("type", "")

    print(f"\n{'═'*50}")
    print(f"[VAPI EVENT] → {event_type}")
    print(f"{'═'*50}")

    try:
        if event_type == "tool-calls":
            return handle_tool_call(message)

        elif event_type == "end-of-call-report":
            return handle_end_of_call(message)

        elif event_type in ("status-update", "hang"):
            return JsonResponse({"status": "ok"})

        else:
            return voice_response(
                "Hello! I'm your property assistant. "
                "You can ask me about any property — price, carpet area, parking, and more."
            )

    except Exception as e:
        logger.error(f"[WEBHOOK ERROR] {str(e)}", exc_info=True)
        return voice_response("Something went wrong. Please try again.")


# ═══════════════════════════════════════════════════════════════
# TOOL CALL HANDLER
# ═══════════════════════════════════════════════════════════════

def handle_tool_call(message: dict) -> JsonResponse:
    tool_calls = message.get("toolCalls", [])

    print("============================")
    print("============================")
    print(tool_calls)
    print("============================")
    print("============================")


    if not tool_calls:
        logger.warning("[TOOL CALL] No tool calls found in message")
        return voice_response("I didn't receive a proper request. Could you repeat that?")

    tool_call    = tool_calls[0]
    tool_call_id = tool_call.get("id", "")
    function     = tool_call.get("function", {})
    fn_name      = function.get("name", "")
    params       = function.get("arguments", {})

    # arguments can arrive as a JSON string — parse it safely
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}

    print(f"[TOOL CALL] Function : {fn_name}")
    print(f"[TOOL CALL] Params   : {params}")

    if fn_name == "search_property":
        result = search_property(params)
        return tool_response(tool_call_id, result)

    # Unknown tool
    logger.warning(f"[TOOL CALL] Unknown function: {fn_name}")
    return tool_response(tool_call_id, "Sorry, I couldn't process that request.")


# ═══════════════════════════════════════════════════════════════
# CORE SEARCH + AI LOGIC
# ═══════════════════════════════════════════════════════════════

def search_property(params: dict) -> str:
    """
    1. Extract filters from Vapi params + fallback text parsing
    2. Query DB with strict filters
    3. Guard rails (no filters / too many results / no results)
    4. Send top MAX_RESULTS_TO_AI properties to Gemini
    5. Return AI answer
    """

    user_question = params.get("user_question", "").strip()
    city          = params.get("city", "").strip()
    property_type = params.get("property_type", "").strip()
    property_name = params.get("property_name", "").strip()
    query_field   = params.get("query_field", "").strip()

    # Use whichever text is available for fallback parsing
    raw_text = (user_question or query_field).lower()

    # ── STEP 1: Extract filters ──────────────────────────────
    city          = extract_city(raw_text, city)
    property_type = extract_property_type(raw_text, property_type)

    print(f"\n[SEARCH PARAMS]")
    print(f"  user_question : {user_question}")
    print(f"  city          : {city}")
    print(f"  property_type : {property_type}")
    print(f"  property_name : {property_name}")
    print(f"  query_field   : {query_field}")

    # ── STEP 2: Guard — no filters at all ───────────────────
    if not city and not property_type and not property_name:
        return (
            "Could you give me a bit more detail? "
            "For example, which city are you interested in, "
            "or what type of property — 2BHK, villa, studio?"
        )

    # ── STEP 3: DB Filter ────────────────────────────────────
    filters = Q(is_active=True)

    if city:
        filters &= Q(city__icontains=city)
    if property_type:
        filters &= Q(property_type__icontains=property_type)
    if property_name:
        filters &= Q(name__icontains=property_name)

    properties = Property.objects.filter(filters)
    count      = properties.count()

    print(f"[DB] Properties found: {count}")

    # ── STEP 4: Guard — too many results ─────────────────────
    if count > FILTER_THRESHOLD:
        parts = []
        if city:
            parts.append(f"in {city}")
        if property_type:
            parts.append(f"of type {property_type}")

        filter_desc = " ".join(parts) or "matching your search"

        return (
            f"I found {count} properties {filter_desc}. "
            "Could you narrow it down a bit? "
            "You can mention the property name, a budget range, or a specific area."
        )

    # ── STEP 5: Guard — no results ───────────────────────────
    if count == 0:
        parts = []
        if property_type:
            parts.append(property_type)
        if city:
            parts.append(f"in {city}")

        search_desc = " ".join(parts) or "matching your criteria"

        return (
            f"Sorry, I couldn't find any {search_desc} properties right now. "
            "Would you like me to check a different city or property type?"
        )

    # ── STEP 6: Build context (max 3 properties) ─────────────
    top_properties = properties[:MAX_RESULTS_TO_AI]
    context        = build_property_context(top_properties)

    print(f"\n[CONTEXT SENT TO AI]\n{context}")

    # ── STEP 7: Get AI answer ─────────────────────────────────
    caller_query = user_question or query_field
    ai_answer    = get_ai_response(
        user_question=caller_query,
        property_data=context
    )

    print(f"\n[AI ANSWER] {ai_answer}")

    # ── STEP 8: Save transcript ───────────────────────────────
    save_transcript(
        property_obj=properties.first(),
        caller_query=caller_query,
        ai_response=ai_answer
    )

    print("REUTNIMG THE RESPINSE OF AI " , ai_answer)
    return ai_answer


# ═══════════════════════════════════════════════════════════════
# END OF CALL HANDLER
# ═══════════════════════════════════════════════════════════════

def handle_end_of_call(message: dict) -> JsonResponse:
    """
    Save full conversation transcript from the end-of-call report.
    Vapi sends alternating user/assistant messages — we pair them up.
    """
    messages = message.get("messages", [])
    saved    = 0
    pending_user_msg = None

    for msg in messages:
        role    = msg.get("role", "")
        content = msg.get("content", "").strip()

        if not content:
            continue

        if role == "user":
            pending_user_msg = content

        elif role == "assistant" and pending_user_msg:
            save_transcript(
                property_obj=None,
                caller_query=pending_user_msg,
                ai_response=content
            )

            print(f"[TRANSCRIPT SAVED]")
            print(f"  User : {pending_user_msg[:80]}")
            print(f"  Bot  : {content[:80]}")

            saved += 1
            pending_user_msg = None

    print(f"[END OF CALL] Total transcripts saved: {saved}")
    return JsonResponse({"status": "saved", "count": saved})