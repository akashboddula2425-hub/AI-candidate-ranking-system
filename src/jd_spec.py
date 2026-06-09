"""
jd_spec.py — A structured, auditable representation of the released Job Description.

This module is the "understanding" layer. Instead of treating the JD as a bag of
keywords, we distill it into the things a great recruiter actually reads for:

  * what the role *is* (retrieval / ranking / recommendation / search at scale)
  * which titles & career arcs signal a real fit vs. a keyword-stuffer
  * which companies are product vs. pure-services (the JD penalises services-only)
  * the explicit disqualifiers the JD lists (research-only, CV/speech-only,
    title-chasers, framework-tutorial enthusiasts, LangChain-only, etc.)
  * the experience band and the location preferences

Everything here is hand-derived from job_description.docx and is fully inspectable.
The dense-retrieval query strings at the bottom are what we embed for the semantic
component, so the lexical and semantic views of the JD stay consistent.
"""

# ---------------------------------------------------------------------------
# 1. Dense-retrieval query (what we embed and match candidate profiles against)
#    A distilled, positive "ideal candidate" description. We keep it focused on
#    what the JD *wants* (not the cultural prose) so the embedding stays sharp.
# ---------------------------------------------------------------------------
JD_QUERY = (
    "Senior AI engineer who owns the intelligence layer of a product: the ranking, "
    "retrieval and matching systems that decide what users see. Production experience "
    "with embeddings-based retrieval (sentence-transformers, BGE, E5), vector databases "
    "and hybrid search (FAISS, Pinecone, Weaviate, Qdrant, Milvus, Elasticsearch, "
    "OpenSearch, pgvector), and recommendation / search / ranking systems shipped "
    "end-to-end to real users at scale at product companies. Strong Python. Designs "
    "evaluation frameworks for ranking quality: NDCG, MRR, MAP, offline-to-online "
    "correlation, A/B testing. Comfortable with LLM integration and fine-tuning "
    "(LoRA, QLoRA, PEFT), learning-to-rank, NLP and information retrieval. A pragmatic "
    "shipper who prefers a working v1 in six weeks over a perfect v2 in six months, "
    "not a research-only academic. 5 to 9 years of experience, based in or willing to "
    "relocate to Noida, Pune, Hyderabad, Bangalore, Mumbai or Delhi NCR in India."
)

# A short facet query used as a secondary semantic signal — the single most
# decisive concept cluster for this role.
JD_QUERY_CORE = (
    "built and shipped a retrieval, ranking, recommendation or search system in "
    "production at a product company; embeddings, vector search, information "
    "retrieval, learning to rank, relevance, semantic search at scale"
)

# A negative query: profiles that look superficially AI but are not a fit
# (used optionally to dampen keyword-only matches).
JD_QUERY_ANTI = (
    "marketing manager, project manager, HR or sales professional excited about GenAI "
    "who took online courses on RAG and vector databases and lists AI buzzwords as "
    "skills; computer vision, image, speech, ASR, TTS specialist without information "
    "retrieval; research-only academic with no production deployment"
)


# ---------------------------------------------------------------------------
# 2. Title relevance. Current title weighted higher than past titles, but we take
#    the *max* across the career arc so an engineer who pivoted is still credited,
#    while a stuffer (all non-eng titles) stays near zero.
#    Matching is done on normalised, lower-cased substrings (see scoring.py).
# ---------------------------------------------------------------------------
# Tier A — the role's core function (1.0)
TITLE_CORE = {
    "ai engineer", "ml engineer", "machine learning engineer", "applied ml engineer",
    "applied scientist", "research scientist (ml)", "recommendation systems engineer",
    "search engineer", "nlp engineer", "relevance engineer", "ranking engineer",
    "search & ranking", "search and ranking",
}
# Tier B — strongly adjacent data-science / applied (0.85)
TITLE_DS = {
    "data scientist", "ai specialist", "ai research engineer",
}
# Tier C — software/data engineering, can hold real retrieval work (0.55–0.7)
TITLE_SWE = {
    "software engineer (ml)", "software engineer ml", "backend engineer",
    "software engineer", "data engineer", "analytics engineer", "platform engineer",
    "full stack developer", "full-stack developer",
}
# Tier D — peripheral tech (0.2–0.35)
TITLE_TECH = {
    "cloud engineer", "devops engineer", "site reliability engineer", "qa engineer",
    "mobile developer", "frontend engineer", "front-end engineer", "java developer",
    ".net developer", "android developer", "ios developer",
}
# Explicitly non-engineering — the keyword-stuffer home turf (~0)
TITLE_NONENG = {
    "marketing manager", "hr manager", "sales executive", "accountant",
    "content writer", "graphic designer", "customer support", "operations manager",
    "business analyst", "project manager", "civil engineer", "mechanical engineer",
    "product manager", "program manager", "recruiter", "financial analyst",
}
# Pure-management titles — the JD down-weights people who stopped writing code.
TITLE_MANAGEMENT = {
    "engineering manager", "director", "vice president", "vp ", "head of",
    "chief", "cto", "ceo",
}

# Seniority words that, combined with an engineering title, indicate the 5-9y band.
SENIORITY_POS = {"senior", "staff", "lead", "principal"}


# ---------------------------------------------------------------------------
# 3. Concept lexicon. Weighted phrases grouped by what they signal. Matched in
#    career-history descriptions + summary (high trust) and, with gating, in the
#    skills list (low trust — a buzzword in a skills list is cheap).
# ---------------------------------------------------------------------------
# The role's bullseye: retrieval / ranking / recsys / search / vector infra.
CONCEPTS_CORE = {
    "retrieval": 1.0, "retriev": 0.9, "ranking": 1.0, "rank ": 0.6, "re-rank": 1.0,
    "rerank": 1.0, "learning to rank": 1.2, "learning-to-rank": 1.2,
    "recommendation": 1.0, "recommender": 1.0, "recsys": 1.1,
    "semantic search": 1.1, "vector search": 1.1, "vector representation": 1.0,
    "information retrieval": 1.2, "search & discovery": 1.0, "search and discovery": 1.0,
    "search infrastructure": 1.0, "search backend": 1.0, "indexing": 0.7,
    "embedding": 1.0, "embeddings": 1.0, "text encoder": 0.9, "content matching": 0.9,
    "bm25": 1.0, "faiss": 0.9, "pinecone": 0.8, "weaviate": 0.8, "qdrant": 0.8,
    "milvus": 0.8, "pgvector": 0.8, "elasticsearch": 0.7, "opensearch": 0.8,
    "nearest neighbor": 0.8, "approximate nearest": 0.9, "hybrid search": 1.1,
    "relevance": 0.8, "haystack": 0.7, "personalization": 0.7, "feed ranking": 1.1,
    "matching": 0.5,
}
# Modern ML systems / production depth.
CONCEPTS_ML = {
    "machine learning": 0.6, "deep learning": 0.5, "nlp": 0.7,
    "natural language": 0.7, "transformer": 0.6, "sentence transformer": 1.0,
    "fine-tun": 0.6, "fine tun": 0.6, "lora": 0.6, "qlora": 0.7, "peft": 0.7,
    "llm": 0.5, "rag": 0.5, "pytorch": 0.6, "tensorflow": 0.5, "scikit": 0.5,
    "mlops": 0.5, "model serving": 0.7, "feature engineering": 0.5,
    "knowledge distillation": 0.6, "model adaptation": 0.7,
}
# Production / scale / evaluation maturity — the JD prizes this heavily.
CONCEPTS_PROD = {
    "production": 0.8, "in production": 1.0, "deployed": 0.8, "at scale": 0.9,
    "real users": 0.9, "latency": 0.6, "throughput": 0.6, "p99": 0.6,
    "a/b test": 1.0, "ab test": 0.9, "experimentation": 0.7,
    "ndcg": 1.1, "mrr": 1.0, "map@": 0.9, "offline": 0.4, "online metric": 0.8,
    "evaluation framework": 1.0, "eval harness": 0.9, "shipped": 0.7,
    "millions of": 0.7, "qps": 0.7,
}
# Nice-to-haves from the JD.
CONCEPTS_BONUS = {
    "hr-tech": 0.8, "hrtech": 0.8, "recruiting": 0.6, "recruitment": 0.6,
    "talent": 0.5, "marketplace": 0.7, "two-sided": 0.7, "distributed systems": 0.6,
    "inference optimization": 0.7, "open-source": 0.6, "open source": 0.6,
    "kaggle": 0.3,
}
# Anti-signals: computer-vision / speech heavy. Not disqualifying alone, but the JD
# says CV/speech/robotics WITHOUT NLP/IR means "re-learning fundamentals here".
CONCEPTS_CV_SPEECH = {
    "yolo": 1.0, "opencv": 1.0, "image classification": 1.0, "object detection": 1.0,
    "computer vision": 1.0, "gans": 0.8, "diffusion model": 0.8, "asr": 1.0,
    "tts": 1.0, "speech recognition": 1.0, "image segmentation": 1.0,
    "facial recognition": 1.0, "pose estimation": 1.0,
}
# Research-only markers. The JD will NOT move forward on pure-research / academic
# backgrounds with no production deployment.
CONCEPTS_RESEARCH = {
    "phd", "ph.d", "postdoc", "post-doc", "academic", "publication", "published",
    "peer-reviewed", "thesis", "dissertation", "professor", "research lab",
    "research-only", "neurips", "icml", "acl ", "cvpr", "research fellow",
}
# Framework-tutorial / LangChain-only enthusiast markers (the JD's "framework
# enthusiasts" and "LangChain to call OpenAI" disqualifiers).
CONCEPTS_TUTORIAL = {
    "online course", "online courses", "self-taught", "tutorial", "bootcamp",
    "ai enthusiast", "genai tools", "experimenting with", "excited about how ai",
    "taking courses",
}


# ---------------------------------------------------------------------------
# 4. Companies. The JD penalises careers spent entirely at IT-services / consulting
#    firms, and prizes product-company experience. We only need a reliable
#    services list; everything else is treated as product-ish.
# ---------------------------------------------------------------------------
SERVICES_FIRMS = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "tech mahindra", "hcl", "hcltech", "mindtree", "mphasis",
    "ltimindtree", "l&t infotech", "lti", "dxc", "hexaware", "genpact",
    "persistent", "birlasoft", "coforge", "nttdata", "ntt data", "atos",
    "iGate".lower(), "syntel", "zensar", "mastek", "cybage",
}
# A non-exhaustive set of recognisable product / tech companies, used as a positive
# signal (presence boosts the product-ratio confidence). Not required to match.
PRODUCT_FIRMS = {
    "google", "meta", "facebook", "amazon", "microsoft", "apple", "netflix",
    "adobe", "linkedin", "nvidia", "uber", "airbnb", "salesforce", "stripe",
    "swiggy", "zomato", "flipkart", "myntra", "cred", "razorpay", "phonepe",
    "paytm", "sarvam", "glance", "yellow.ai", "verloop", "locobuzz", "wysa",
    "niramai", "ola", "sharechat", "meesho", "groww", "zerodha", "postman",
    "freshworks", "browserstack", "hasura", "dunzo", "urban company", "navi",
}


# ---------------------------------------------------------------------------
# 5. Experience band & location preferences (from the JD).
# ---------------------------------------------------------------------------
EXP_IDEAL_LO, EXP_IDEAL_HI = 6.0, 8.0     # the JD's "ideal" 6-8y
EXP_BAND_LO, EXP_BAND_HI = 5.0, 9.0       # the stated 5-9y band

# Strong location match (Noida / Pune preferred), then welcome cities, then India,
# then abroad (no visa sponsorship → discount).
LOC_PREFERRED = {"noida", "pune"}
LOC_WELCOME = {"hyderabad", "mumbai", "delhi", "gurgaon", "gurugram", "bangalore",
               "bengaluru", "noida", "pune", "ncr"}
INDIA = "india"
