from flask import Flask, request, jsonify, send_from_directory
import requests
import re
import os
import unicodedata

# ============================================================
# RURAL HEALTH AI
# Flask + Ollama + Gemma 3:1b
# Multilingual: English / Tamil / Hindi
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    static_folder=STATIC_DIR
)

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"

MODEL_NAME = "gemma3:1b"

MAX_MESSAGE_LENGTH = 500
OLLAMA_TIMEOUT = 120

SUPPORTED_LANGUAGES = {"en", "ta", "hi"}

# ============================================================
# LANGUAGE NAMES
# ============================================================

LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi"
}

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Rural Health AI.

You are a health-awareness assistant designed for rural
communities in India.

Your job is to provide simple, safe, accurate and relevant
health-awareness information.

============================================================
STRICT LANGUAGE RULES
============================================================

The required response language is explicitly provided.

If REQUIRED LANGUAGE is ENGLISH:
- Respond ONLY in natural, simple English.
- Use correct English grammar.
- Do not use Tamil or Hindi unless they are necessary medical
  names that are normally written in English.

If REQUIRED LANGUAGE is TAMIL:
- Respond ONLY in natural, simple Tamil.
- Use proper Tamil grammar.
- Use commonly understood Tamil words.
- Common English medical terms are allowed when necessary.
- Do NOT invent Tamil words.
- Do NOT translate medical terms into strange or artificial
  Tamil.
- Do NOT randomly switch to English or Hindi.
- If the user uses Thanglish but the required language is Tamil,
  understand the meaning and answer in proper Tamil.

If REQUIRED LANGUAGE is HINDI:
- Respond ONLY in natural, simple Hindi.
- Use correct Hindi grammar.
- Use commonly understood Hindi words.
- Common English medical terms are allowed when necessary.
- Do NOT invent Hindi words.
- Do NOT use strange machine-translated Hindi.
- Do NOT randomly switch to English or Tamil.

============================================================
QUALITY RULES
============================================================

- Answer exactly what the user asks.
- Use correct grammar.
- Use natural human-readable language.
- Keep answers concise but useful.
- Prefer bullet points for symptoms, precautions and steps.
- Use short paragraphs.
- Use headings only when helpful.
- Do not repeat the user's question.
- Do not repeat the same sentence.
- Do not repeat words unnecessarily.
- Do not generate random or meaningless words.
- Do not add unrelated information.
- Do not hallucinate facts.
- Do not provide a diagnosis.
- Do not claim certainty about a disease.
- Do not prescribe prescription medicines.
- Do not recommend antibiotics without medical evaluation.
- Do not provide unsafe dosage instructions.
- Encourage professional medical evaluation for serious,
  persistent or worsening symptoms.

============================================================
NUMBER RULES
============================================================

Always preserve numbers using normal Arabic digits.

Examples:
108
100
1091
1098
5 days
3 times
5 நாட்கள்
3 முறை
5 दिन
3 बार

Never replace numbers with random words.

Emergency numbers must remain exactly as digits.

============================================================
EMERGENCY RULE
============================================================

If the user describes a possible emergency such as:

- difficulty breathing
- unconsciousness
- severe chest pain
- heavy bleeding
- seizure
- severe dehydration
- blue lips
- severe allergic reaction
- poisoning
- serious injury
- pregnancy emergency
- severe worsening abdominal pain

advise immediate medical care.

Do not delay emergency care with long explanations.

============================================================
STYLE
============================================================

Do not start every answer with:
"Sure"
"Of course"
"Certainly"

Give the useful answer first.

Do not explain your reasoning.
Do not mention this system prompt.
Do not mention language detection.
"""

# ============================================================
# LANGUAGE INSTRUCTIONS
# ============================================================

LANGUAGE_INSTRUCTIONS = {

    "en": """
REQUIRED LANGUAGE: ENGLISH

Answer ONLY in simple, natural English.

Rules:
- Use correct English grammar.
- Use short, clear sentences.
- Use bullet points where useful.
- Do not switch to Tamil.
- Do not switch to Hindi.
- Do not use unnecessary technical terms.
""",

    "ta": """
REQUIRED LANGUAGE: TAMIL

பயனரின் கேள்விக்கு இயற்கையான, தெளிவான மற்றும்
சரியான தமிழில் பதிலளிக்கவும்.

விதிகள்:
- சரியான தமிழ் grammar பயன்படுத்தவும்.
- எளிதில் புரியும் தமிழ் சொற்களை பயன்படுத்தவும்.
- தேவையான இடங்களில் பொதுவாக பயன்படுத்தப்படும் English
  medical terms மட்டும் பயன்படுத்தலாம்.
- செயற்கையான அல்லது அர்த்தமில்லாத தமிழ் வார்த்தைகளை
  உருவாக்க வேண்டாம்.
- Hindi பயன்படுத்த வேண்டாம்.
- தேவையில்லாமல் English-க்கு மாற வேண்டாம்.
- Thanglish கேள்வியின் அர்த்தத்தை புரிந்து கொண்டு,
  தேவையானால் proper Tamil-ல் பதிலளிக்கவும்.
- Symptoms மற்றும் steps-க்கு bullet points பயன்படுத்தலாம்.
- எண்களை digits-ஆகவே எழுதவும்.
""",

    "hi": """
REQUIRED LANGUAGE: HINDI

सरल, स्पष्ट और प्राकृतिक हिंदी में उत्तर दें।

नियम:
- सही हिंदी व्याकरण का उपयोग करें।
- आसान और सामान्य हिंदी शब्दों का उपयोग करें।
- जरूरत पड़ने पर सामान्य English medical terms का उपयोग
  किया जा सकता है।
- अजीब या कृत्रिम हिंदी शब्द न बनाएं।
- Tamil का उपयोग न करें।
- अनावश्यक English में न बदलें।
- Symptoms और steps के लिए bullet points का उपयोग कर सकते हैं।
- संख्याओं को सामान्य digits में ही लिखें।
"""
}

# ============================================================
# EMERGENCY PATTERNS
# ============================================================

EMERGENCY_PATTERNS = [

    # English
    r"\bdifficulty breathing\b",
    r"\bbreathing difficulty\b",
    r"\bcan't breathe\b",
    r"\bcannot breathe\b",
    r"\bshortness of breath\b",
    r"\bsevere chest pain\b",
    r"\bunconscious\b",
    r"\bheavy bleeding\b",
    r"\bseizure\b",
    r"\bpoisoning\b",
    r"\bsevere dehydration\b",
    r"\bblue lips\b",
    r"\bsevere allergic reaction\b",
    r"\bserious injury\b",

    # Tamil
    r"மூச்சுத்திணறல்",
    r"மூச்சு விட முடிய",
    r"மூச்சு விடுவதில் சிரமம்",
    r"மூச்சு திணறல்",
    r"கடுமையான மார்பு வலி",
    r"நினைவிழப்பு",
    r"அதிக இரத்தப்போக்கு",
    r"வலிப்பு",
    r"விஷம்",
    r"கடுமையான நீரிழப்பு",
    r"நீல நிற உதடு",
    r"கடுமையான காயம்",

    # Hindi
    r"सांस लेने में कठिनाई",
    r"सांस लेने में दिक्कत",
    r"सांस नहीं आ",
    r"सांस लेने में परेशानी",
    r"सीने में तेज दर्द",
    r"सीने में गंभीर दर्द",
    r"बेहोश",
    r"बहुत ज्यादा खून",
    r"दौरा",
    r"जहर",
    r"गंभीर निर्जलीकरण",
    r"नीले होंठ",
    r"गंभीर चोट"
]

# ============================================================
# EMERGENCY RESPONSE
# ============================================================

def emergency_message(language):

    if language == "ta":

        return (
            "⚠️ இது அவசர நிலையாக இருக்கலாம்.\n\n"
            "• உடனடியாக அருகிலுள்ள மருத்துவமனைக்கு செல்லுங்கள்.\n"
            "• Ambulance உதவிக்கு 108 அழைக்கவும்.\n"
            "• நிலைமை மோசமாக இருந்தால் தனியாக இருக்க வேண்டாம்.\n"
            "• தாமதிக்காமல் மருத்துவ உதவியை பெறுங்கள்."
        )

    if language == "hi":

        return (
            "⚠️ यह एक आपातकालीन स्थिति हो सकती है।\n\n"
            "• तुरंत नजदीकी अस्पताल जाएं।\n"
            "• Ambulance के लिए 108 पर कॉल करें।\n"
            "• स्थिति गंभीर होने पर अकेले न रहें।\n"
            "• बिना देरी किए चिकित्सा सहायता लें।"
        )

    return (
        "⚠️ This may be an emergency.\n\n"
        "• Go to the nearest hospital immediately.\n"
        "• Call 108 for an ambulance.\n"
        "• Do not stay alone if the condition is severe.\n"
        "• Get medical help without delay."
    )

# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(text):

    if not text:
        return "en"

    text = unicodedata.normalize(
        "NFKC",
        str(text)
    )

    tamil_count = len(
        re.findall(
            r"[\u0B80-\u0BFF]",
            text
        )
    )

    hindi_count = len(
        re.findall(
            r"[\u0900-\u097F]",
            text
        )
    )

    english_count = len(
        re.findall(
            r"[A-Za-z]",
            text
        )
    )

    # Clear Tamil
    if tamil_count > 0 and tamil_count >= hindi_count:
        return "ta"

    # Clear Hindi
    if hindi_count > 0 and hindi_count > tamil_count:
        return "hi"

    # English / Thanglish
    if english_count > 0:
        return "en"

    return "en"

# ============================================================
# EMERGENCY DETECTION
# ============================================================

def is_emergency(message):

    text = unicodedata.normalize(
        "NFKC",
        str(message).lower().strip()
    )

    for pattern in EMERGENCY_PATTERNS:

        if re.search(
            pattern,
            text,
            re.IGNORECASE
        ):
            return True

    return False

# ============================================================
# RESPONSE CLEANING
# ============================================================

def clean_response(text):

    if not text:
        return ""

    text = str(text).strip()

    # Remove common model prefixes
    prefixes = [
        "assistant:",
        "Assistant:",
        "AI:",
        "ai:",
        "Response:",
        "response:",
        "Answer:",
        "answer:"
    ]

    for prefix in prefixes:

        if text.startswith(prefix):

            text = text[
                len(prefix):
            ].strip()

    # Remove excessive spaces
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text
    )

    # Normalize excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    # --------------------------------------------------------
    # Remove duplicate identical lines
    # --------------------------------------------------------

    lines = text.splitlines()

    cleaned_lines = []
    seen_lines = set()

    for line in lines:

        stripped = line.strip()

        if not stripped:
            cleaned_lines.append("")
            continue

        normalized = re.sub(
            r"\s+",
            " ",
            stripped.lower()
        )

        if normalized in seen_lines:
            continue

        seen_lines.add(normalized)
        cleaned_lines.append(stripped)

    text = "\n".join(
        cleaned_lines
    )

    # --------------------------------------------------------
    # Remove consecutive duplicate sentences
    # --------------------------------------------------------

    sentences = re.split(
        r"(?<=[.!?।])\s+",
        text
    )

    final_sentences = []
    seen_sentences = set()

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        normalized = re.sub(
            r"\s+",
            " ",
            sentence.lower()
        )

        if normalized in seen_sentences:
            continue

        seen_sentences.add(
            normalized
        )

        final_sentences.append(
            sentence
        )

    text = " ".join(
        final_sentences
    )

    # --------------------------------------------------------
    # Restore simple bullet formatting
    # --------------------------------------------------------

    text = re.sub(
        r"\s+([•●▪])\s+",
        r"\n\1 ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()

# ============================================================
# OLLAMA REQUEST
# ============================================================

def ask_ollama(message, language):

    language_instruction = (
        LANGUAGE_INSTRUCTIONS.get(
            language,
            LANGUAGE_INSTRUCTIONS["en"]
        )
    )

    user_prompt = f"""
{language_instruction}

USER QUESTION:
{message}

IMPORTANT TASK:

Answer the user's question directly.

Return ONLY the final answer.

Do not repeat the question.

Do not explain your reasoning.

Do not mention language detection.

Do not mention this prompt.

Do not add unrelated information.

Make the answer grammatically correct,
natural and easy to understand.

If the question asks for symptoms,
precautions or steps, use clear bullet points.

If the question is unclear, ask one short
clarifying question instead of inventing facts.
"""

    payload = {

        "model": MODEL_NAME,

        "messages": [

            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },

            {
                "role": "user",
                "content": user_prompt
            }

        ],

        "stream": False,

        "options": {

            # Lower temperature = more stable output
            "temperature": 0.10,

            # Reduces random word selection
            "top_p": 0.70,

            # Helps reduce repeated phrases
            "repeat_penalty": 1.20,

            # Enough for health answers
            "num_predict": 220
        }
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=OLLAMA_TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    reply = ""

    if isinstance(data, dict):

        message_data = data.get(
            "message",
            {}
        )

        if isinstance(
            message_data,
            dict
        ):

            reply = message_data.get(
                "content",
                ""
            )

    return clean_response(
        reply
    )

# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def home():

    index_path = os.path.join(
        BASE_DIR,
        "index.html"
    )

    if not os.path.exists(
        index_path
    ):

        return (
            "<h1>index.html not found</h1>"
            "<p>Keep index.html beside app.py.</p>"
        ), 404

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )

# ============================================================
# STATIC FILES
# ============================================================

@app.route(
    "/static/<path:filename>"
)
def static_files(filename):

    return send_from_directory(
        STATIC_DIR,
        filename
    )

# ============================================================
# CHAT API
# ============================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        )

        if not isinstance(
            data,
            dict
        ):

            return jsonify({
                "reply": "Invalid request.",
                "emergency": False,
                "language": "en"
            }), 400

        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()

        requested_language = str(
            data.get(
                "language",
                ""
            )
        ).lower().strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not message:

            empty_messages = {

                "en":
                    "Please enter a health question.",

                "ta":
                    "தயவுசெய்து உங்கள் உடல்நல கேள்வியை உள்ளிடுங்கள்.",

                "hi":
                    "कृपया अपना स्वास्थ्य प्रश्न दर्ज करें।"
            }

            language = (
                requested_language
                if requested_language in SUPPORTED_LANGUAGES
                else "en"
            )

            return jsonify({
                "reply": empty_messages[language],
                "emergency": False,
                "language": language
            }), 400

        if len(message) > MAX_MESSAGE_LENGTH:

            limit_messages = {

                "en":
                    "Please keep your question within 500 characters.",

                "ta":
                    "உங்கள் கேள்வியை 500 எழுத்துகளுக்குள் வைத்திருக்கவும்.",

                "hi":
                    "कृपया अपना प्रश्न 500 अक्षरों के भीतर रखें।"
            }

            language = (
                requested_language
                if requested_language in SUPPORTED_LANGUAGES
                else detect_language(message)
            )

            return jsonify({
                "reply": limit_messages[language],
                "emergency": False,
                "language": language
            }), 400

        # ----------------------------------------------------
        # LANGUAGE
        # ----------------------------------------------------

        detected_language = detect_language(
            message
        )

        if detected_language in {"ta", "hi"}:

            # Script is more reliable than UI selection
            # when Tamil/Hindi characters are actually present.
            language = detected_language

        elif requested_language in SUPPORTED_LANGUAGES:

            language = requested_language

        else:

            language = detected_language

        # ----------------------------------------------------
        # EMERGENCY
        # ----------------------------------------------------

        emergency = is_emergency(
            message
        )

        if emergency:

            return jsonify({

                "reply":
                    emergency_message(
                        language
                    ),

                "emergency": True,

                "language": language

            })

        # ----------------------------------------------------
        # OLLAMA
        # ----------------------------------------------------

        reply = ask_ollama(
            message,
            language
        )

        # ----------------------------------------------------
        # EMPTY RESPONSE
        # ----------------------------------------------------

        if not reply:

            fallback_messages = {

                "en":
                    "Sorry, I could not generate a response right now. Please try again.",

                "ta":
                    "மன்னிக்கவும். தற்போது பதிலை உருவாக்க முடியவில்லை. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",

                "hi":
                    "क्षमा करें। अभी उत्तर तैयार नहीं किया जा सका। कृपया थोड़ी देर बाद फिर प्रयास करें।"
            }

            reply = fallback_messages[
                language
            ]

        # ----------------------------------------------------
        # FINAL RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "reply": reply,

            "emergency": False,

            "language": language

        })

    # ========================================================
    # OLLAMA CONNECTION ERROR
    # ========================================================

    except requests.exceptions.ConnectionError:

        error_messages = {

            "en":
                "Ollama is not running. Please start Ollama and make sure Gemma 3:1b is installed.",

            "ta":
                "Ollama இயங்கவில்லை. Ollama-வை தொடங்கி Gemma 3:1b நிறுவப்பட்டுள்ளதா என்பதை சரிபார்க்கவும்.",

            "hi":
                "Ollama चल नहीं रहा है। Ollama शुरू करें और सुनिश्चित करें कि Gemma 3:1b इंस्टॉल है।"
        }

        language = (
            requested_language
            if "requested_language" in locals()
            and requested_language in SUPPORTED_LANGUAGES
            else "en"
        )

        return jsonify({

            "reply":
                error_messages[language],

            "emergency": False,

            "language": language

        }), 503

    # ========================================================
    # TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        timeout_messages = {

            "en":
                "The AI is taking too long to respond. Please try again.",

            "ta":
                "AI பதில் அளிக்க அதிக நேரம் எடுத்துக்கொள்கிறது. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",

            "hi":
                "AI उत्तर देने में अधिक समय ले रहा है। कृपया फिर से प्रयास करें।"
        }

        language = (
            requested_language
            if "requested_language" in locals()
            and requested_language in SUPPORTED_LANGUAGES
            else "en"
        )

        return jsonify({

            "reply":
                timeout_messages[language],

            "emergency": False,

            "language": language

        }), 504

    # ========================================================
    # OLLAMA HTTP ERROR
    # ========================================================

    except requests.exceptions.HTTPError as error:

        print(
            "OLLAMA HTTP ERROR:",
            error
        )

        http_messages = {

            "en":
                "The local AI model returned an error. Please check Ollama and Gemma 3:1b.",

            "ta":
                "Local AI model-ல் பிழை ஏற்பட்டுள்ளது. Ollama மற்றும் Gemma 3:1b-ஐ சரிபார்க்கவும்.",

            "hi":
                "Local AI model में त्रुटि हुई। Ollama और Gemma 3:1b की जांच करें।"
        }

        language = (
            requested_language
            if "requested_language" in locals()
            and requested_language in SUPPORTED_LANGUAGES
            else "en"
        )

        return jsonify({

            "reply":
                http_messages[language],

            "emergency": False,

            "language": language

        }), 502

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as error:

        print(
            "CHAT ERROR:",
            repr(error)
        )

        generic_messages = {

            "en":
                "Sorry, something went wrong. Please check Ollama and try again.",

            "ta":
                "மன்னிக்கவும். ஒரு பிழை ஏற்பட்டுள்ளது. Ollama-வை சரிபார்த்து மீண்டும் முயற்சிக்கவும்.",

            "hi":
                "क्षमा करें। कुछ समस्या हुई है। Ollama की जांच करके फिर प्रयास करें।"
        }

        language = (
            requested_language
            if "requested_language" in locals()
            and requested_language in SUPPORTED_LANGUAGES
            else "en"
        )

        return jsonify({

            "reply":
                generic_messages[language],

            "emergency": False,

            "language": language

        }), 500

# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    try:

        response = requests.get(
            OLLAMA_TAGS_URL,
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        models = data.get(
            "models",
            []
        )

        model_found = any(

            model.get("name") == MODEL_NAME

            for model in models

        )

        return jsonify({

            "status": "ok",

            "ollama": True,

            "model": MODEL_NAME,

            "model_available":
                model_found

        })

    except Exception as error:

        print(
            "HEALTH CHECK ERROR:",
            repr(error)
        )

        return jsonify({

            "status": "error",

            "ollama": False,

            "model": MODEL_NAME,

            "model_available": False

        }), 503

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("RURAL HEALTH AI")
    print("=" * 60)

    print(
        "Base folder :",
        BASE_DIR
    )

    print(
        "Index file  :",
        os.path.join(
            BASE_DIR,
            "index.html"
        )
    )

    print(
        "Model       :",
        MODEL_NAME
    )

    print(
        "Ollama      :",
        OLLAMA_URL
    )

    print(
        "Server      :",
        "http://127.0.0.1:5000"
    )

    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )