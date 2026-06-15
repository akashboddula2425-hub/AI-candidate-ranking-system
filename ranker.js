/* ranker.js — in-browser port of the Redrob hybrid ranker scoring pipeline.
   Faithful to the Python in src/ (jd_spec, profile, features, integrity,
   behavioral, scoring, reasoning). Semantic similarity is supplied by
   embeddings.js (transformers.js); everything else runs here, in the browser. */

// ---------------------------------------------------------------- JD spec
export const JD_QUERY =
  "Senior AI engineer who owns the intelligence layer of a product: the ranking, " +
  "retrieval and matching systems that decide what users see. Production experience " +
  "with embeddings-based retrieval (sentence-transformers, BGE, E5), vector databases " +
  "and hybrid search (FAISS, Pinecone, Weaviate, Qdrant, Milvus, Elasticsearch, " +
  "OpenSearch, pgvector), and recommendation / search / ranking systems shipped " +
  "end-to-end to real users at scale at product companies. Strong Python. Designs " +
  "evaluation frameworks for ranking quality: NDCG, MRR, MAP, offline-to-online " +
  "correlation, A/B testing. Comfortable with LLM integration and fine-tuning " +
  "(LoRA, QLoRA, PEFT), learning-to-rank, NLP and information retrieval. A pragmatic " +
  "shipper who prefers a working v1 in six weeks over a perfect v2 in six months, " +
  "not a research-only academic. 5 to 9 years of experience, based in or willing to " +
  "relocate to Noida, Pune, Hyderabad, Bangalore, Mumbai or Delhi NCR in India.";
export const JD_QUERY_CORE =
  "built and shipped a retrieval, ranking, recommendation or search system in " +
  "production at a product company; embeddings, vector search, information " +
  "retrieval, learning to rank, relevance, semantic search at scale";
export const JD_QUERY_ANTI =
  "marketing manager, project manager, HR or sales professional excited about GenAI " +
  "who took online courses on RAG and vector databases and lists AI buzzwords as " +
  "skills; computer vision, image, speech, ASR, TTS specialist without information " +
  "retrieval; research-only academic with no production deployment";
export const JD_QUERIES = [JD_QUERY, JD_QUERY_CORE, JD_QUERY_ANTI];

const TITLE_CORE = ["ai engineer","ml engineer","machine learning engineer","applied ml engineer",
  "applied scientist","research scientist (ml)","recommendation systems engineer","search engineer",
  "nlp engineer","relevance engineer","ranking engineer","search & ranking","search and ranking"];
const TITLE_DS = ["data scientist","ai specialist","ai research engineer"];
const TITLE_SWE = ["software engineer (ml)","software engineer ml","backend engineer",
  "software engineer","data engineer","analytics engineer","platform engineer",
  "full stack developer","full-stack developer"];
const TITLE_TECH = ["cloud engineer","devops engineer","site reliability engineer","qa engineer",
  "mobile developer","frontend engineer","front-end engineer","java developer",".net developer",
  "android developer","ios developer"];
const TITLE_NONENG = ["marketing manager","hr manager","sales executive","accountant",
  "content writer","graphic designer","customer support","operations manager","business analyst",
  "project manager","civil engineer","mechanical engineer","product manager","program manager",
  "recruiter","financial analyst"];
const TITLE_MANAGEMENT = ["engineering manager","director","vice president","vp ","head of","chief","cto","ceo"];

const CONCEPTS_CORE = {"retrieval":1.0,"retriev":0.9,"ranking":1.0,"rank ":0.6,"re-rank":1.0,
  "rerank":1.0,"learning to rank":1.2,"learning-to-rank":1.2,"recommendation":1.0,"recommender":1.0,
  "recsys":1.1,"semantic search":1.1,"vector search":1.1,"vector representation":1.0,
  "information retrieval":1.2,"search & discovery":1.0,"search and discovery":1.0,
  "search infrastructure":1.0,"search backend":1.0,"indexing":0.7,"embedding":1.0,"embeddings":1.0,
  "text encoder":0.9,"content matching":0.9,"bm25":1.0,"faiss":0.9,"pinecone":0.8,"weaviate":0.8,
  "qdrant":0.8,"milvus":0.8,"pgvector":0.8,"elasticsearch":0.7,"opensearch":0.8,"nearest neighbor":0.8,
  "approximate nearest":0.9,"hybrid search":1.1,"relevance":0.8,"haystack":0.7,"personalization":0.7,
  "feed ranking":1.1,"matching":0.5};
const CONCEPTS_ML = {"machine learning":0.6,"deep learning":0.5,"nlp":0.7,"natural language":0.7,
  "transformer":0.6,"sentence transformer":1.0,"fine-tun":0.6,"fine tun":0.6,"lora":0.6,"qlora":0.7,
  "peft":0.7,"llm":0.5,"rag":0.5,"pytorch":0.6,"tensorflow":0.5,"scikit":0.5,"mlops":0.5,
  "model serving":0.7,"feature engineering":0.5,"knowledge distillation":0.6,"model adaptation":0.7};
const CONCEPTS_PROD = {"production":0.8,"in production":1.0,"deployed":0.8,"at scale":0.9,
  "real users":0.9,"latency":0.6,"throughput":0.6,"p99":0.6,"a/b test":1.0,"ab test":0.9,
  "experimentation":0.7,"ndcg":1.1,"mrr":1.0,"map@":0.9,"offline":0.4,"online metric":0.8,
  "evaluation framework":1.0,"eval harness":0.9,"shipped":0.7,"millions of":0.7,"qps":0.7};
const CONCEPTS_BONUS = {"hr-tech":0.8,"hrtech":0.8,"recruiting":0.6,"recruitment":0.6,"talent":0.5,
  "marketplace":0.7,"two-sided":0.7,"distributed systems":0.6,"inference optimization":0.7,
  "open-source":0.6,"open source":0.6,"kaggle":0.3};
const CONCEPTS_CV_SPEECH = {"yolo":1.0,"opencv":1.0,"image classification":1.0,"object detection":1.0,
  "computer vision":1.0,"gans":0.8,"diffusion model":0.8,"asr":1.0,"tts":1.0,"speech recognition":1.0,
  "image segmentation":1.0,"facial recognition":1.0,"pose estimation":1.0};
const CONCEPTS_RESEARCH = ["phd","ph.d","postdoc","post-doc","academic","publication","published",
  "peer-reviewed","thesis","dissertation","professor","research lab","research-only","neurips",
  "icml","acl ","cvpr","research fellow"];
const CONCEPTS_TUTORIAL = ["online course","online courses","self-taught","tutorial","bootcamp",
  "ai enthusiast","genai tools","experimenting with","excited about how ai","taking courses"];
const SERVICES_FIRMS = ["tcs","tata consultancy","infosys","wipro","accenture","cognizant","capgemini",
  "tech mahindra","hcl","hcltech","mindtree","mphasis","ltimindtree","l&t infotech","lti","dxc",
  "hexaware","genpact","persistent","birlasoft","coforge","nttdata","ntt data","atos","igate",
  "syntel","zensar","mastek","cybage"];
const PRODUCT_FIRMS = ["google","meta","facebook","amazon","microsoft","apple","netflix","adobe",
  "linkedin","nvidia","uber","airbnb","salesforce","stripe","swiggy","zomato","flipkart","myntra",
  "cred","razorpay","phonepe","paytm","sarvam","glance","yellow.ai","verloop","locobuzz","wysa",
  "niramai","ola","sharechat","meesho","groww","zerodha","postman","freshworks","browserstack",
  "hasura","dunzo","urban company","navi"];
const EXP_IDEAL_LO = 6.0, EXP_IDEAL_HI = 8.0;
const LOC_PREFERRED = ["noida","pune"];
const LOC_WELCOME = ["hyderabad","mumbai","delhi","gurgaon","gurugram","bangalore","bengaluru","noida","pune","ncr"];
const AI_BUZZ = new Set(["rag","pinecone","embeddings","vector search","semantic search","langchain",
  "llms","sentence transformers","hugging face transformers","information retrieval",
  "recommendation systems","faiss","fine-tuning llms","prompt engineering","weaviate","qdrant","milvus"]);
const CV_SKILLS = new Set(["yolo","opencv","computer vision","object detection","image classification",
  "asr","tts","speech recognition","gans","diffusion models","cnn"]);

// ---------------------------------------------------------------- profile utils
export const TODAY = new Date(Date.UTC(2026, 5, 9));
function parseDate(s){ if(!s||typeof s!=="string") return null;
  const p=s.split("-"); if(p.length<3) return null;
  const y=+p[0],m=+p[1],d=+p[2]; if(!y||!m||!d) return null;
  return new Date(Date.UTC(y,m-1,d)); }
function monthsBetween(a,b){ return (b.getUTCFullYear()-a.getUTCFullYear())*12 + (b.getUTCMonth()-a.getUTCMonth()); }
function daysSince(d){ return Math.floor((TODAY - d)/86400000); }
export function norm(s){ if(!s) return ""; return String(s).toLowerCase()
  .replace(/[—–]/g," ").replace(/\s+/g," ").trim(); }

export function semanticDocument(c, maxChars=1100){
  const p=c.profile||{}; const parts=[p.headline||"", p.summary||"",
    `${p.current_title||""} at ${p.current_company||""}.`];
  for(const h of (c.career_history||[]).slice(0,2)) parts.push(`${h.title||""}: ${h.description||""}`);
  const sk=c.skills||[]; if(sk.length) parts.push("Skills: "+sk.map(s=>s.name||"").join(", "));
  return parts.filter(x=>x&&x.trim()).join(" ").slice(0,maxChars);
}
function careerText(c){ const p=c.profile||{}; const parts=[p.headline||"",p.summary||""];
  for(const h of (c.career_history||[])){ parts.push(h.title||""); parts.push(h.description||""); }
  return norm(parts.join("\n")); }
function skillNames(c){ return (c.skills||[]).map(s=>norm(s.name||"")); }
function allTitles(c){ const p=c.profile||{}; const out=[norm(p.current_title||"")];
  for(const h of (c.career_history||[])) out.push(norm(h.title||"")); return out.filter(t=>t); }

export class Candidate{
  constructor(raw){ this.raw=raw; this.id=raw.candidate_id||""; this.profile=raw.profile||{};
    this.signals=raw.redrob_signals||{}; this.career=raw.career_history||[]; this.skills=raw.skills||[];
    this.ctext=careerText(raw); this.titles=allTitles(raw);
    this.skillList=[...new Set(skillNames(raw))]; this.skillSet=new Set(this.skillList);
    this.yoe=parseFloat(this.profile.years_of_experience||0)||0; }
}

// ---------------------------------------------------------------- features
function titleWeight(t){ let best=0;
  for(const k of TITLE_CORE) if(t.includes(k)) best=Math.max(best,1.0);
  for(const k of TITLE_DS) if(t.includes(k)) best=Math.max(best,0.85);
  for(const k of TITLE_SWE) if(t.includes(k)) best=Math.max(best,(t.includes("backend")||t.includes("software"))?0.62:0.5);
  if(t.includes("software engineer")&&(t.includes("ml")||t.includes("machine learning"))) best=Math.max(best,0.85);
  for(const k of TITLE_TECH) if(t.includes(k)) best=Math.max(best,0.22);
  if(best<0.3){ for(const k of TITLE_NONENG) if(t.includes(k)) return 0.03; }
  return best; }
function titleFit(c){ const cur=norm(c.profile.current_title||""); const curW=titleWeight(cur);
  let pastW=0, bestPast=""; for(const h of c.career.slice(1)){ const w=titleWeight(norm(h.title||""));
    if(w>pastW){ pastW=w; bestPast=h.title||""; } }
  let score=Math.max(curW, 0.85*pastW);
  const padded=" "+cur+" "; const mgmt=TITLE_MANAGEMENT.some(k=>padded.includes(k));
  if(mgmt && !cur.includes("engineer") && curW<0.5) score*=0.7;
  return [score, {current_title:c.profile.current_title||"", current_w:curW, best_past:bestPast}]; }

function weightedHits(text, lex){ let total=0; const hits=[];
  for(const [ph,w] of Object.entries(lex)) if(text.includes(ph)){ total+=w; hits.push(ph.trim()); }
  return [total, hits]; }
const sat=(x,k)=>1-Math.exp(-x/k);
function domainFit(c, titleScore){ const t=c.ctext;
  const [coreT,coreHits]=weightedHits(t,CONCEPTS_CORE);
  const [mlT,mlHits]=weightedHits(t,CONCEPTS_ML);
  const [prodT,prodHits]=weightedHits(t,CONCEPTS_PROD);
  const [bonusT]=weightedHits(t,CONCEPTS_BONUS);
  const blob=" | "+c.skillList.join(" | ")+" | ";
  const skCore=weightedHits(blob,CONCEPTS_CORE)[0], skMl=weightedHits(blob,CONCEPTS_ML)[0];
  const gate=Math.min(1.0, 0.15+titleScore);
  const skillsCredit=0.25*(skCore+0.5*skMl)*gate;
  const raw=1.5*sat(coreT,2.5)+0.7*sat(mlT,3.0)+0.9*sat(prodT,2.5)+0.4*sat(bonusT,2.0)+0.5*sat(skillsCredit,1.5);
  return [Math.min(raw/4.0,1.0), {core_hits:coreHits, ml_hits:mlHits, prod_hits:prodHits, core_t:coreT, prod_t:prodT}]; }

function experienceFit(c){ const y=c.yoe; let s;
  if(y>=EXP_IDEAL_LO && y<=EXP_IDEAL_HI) s=1.0;
  else if(y<EXP_IDEAL_LO) s=Math.max(0.15,(y-1)/(EXP_IDEAL_LO-1));
  else s=Math.max(0.3, 1.0-(y-EXP_IDEAL_HI)*0.09);
  return [s,{yoe:y}]; }

function careerArc(c){ let monthsTotal=0; for(const h of c.career) monthsTotal+=(h.duration_months||0);
  monthsTotal=monthsTotal||1; let servicesM=0, productHits=0, shortStints=0;
  for(const h of c.career){ const comp=norm(h.company||""); const dm=h.duration_months||0;
    if(SERVICES_FIRMS.some(f=>comp.includes(f))) servicesM+=dm;
    if(PRODUCT_FIRMS.some(f=>comp.includes(f))) productHits++;
    if(dm>0 && dm<20) shortStints++; }
  const productRatio=1.0-servicesM/monthsTotal; const njobs=c.career.length;
  const avgTenure=monthsTotal/Math.max(njobs,1);
  const hopper=(njobs>=4 && avgTenure<18) || shortStints>=3;
  let score=0.55*productRatio+0.25;
  if(productHits) score+=Math.min(0.15,0.05*productHits);
  if(avgTenure>=24) score+=0.1; if(hopper) score-=0.25;
  score=Math.max(0,Math.min(1,score));
  return [score,{product_ratio:productRatio, avg_tenure:avgTenure, hopper}]; }

function locationFit(c){ const loc=norm(c.profile.location||""); const country=norm(c.profile.country||"");
  const relo=!!c.signals.willing_to_relocate;
  if(LOC_PREFERRED.some(x=>loc.includes(x))) return [1.0,{}];
  if(LOC_WELCOME.some(x=>loc.includes(x))) return [0.9,{}];
  if(country.includes("india")) return [relo?0.72:0.6,{}];
  return [relo?0.35:0.2,{}]; }

function disqualifierPenalty(c, dev){ let pen=1.0; const reasons=[]; const t=c.ctext;
  const cvT=weightedHits(t,CONCEPTS_CV_SPEECH)[0];
  let cvSkills=0; for(const s of c.skillSet) if(CV_SKILLS.has(s)) cvSkills++;
  const irPresent=(dev.core_t||0)>1.0;
  if((cvT>=2.0||cvSkills>=4)&&!irPresent){ pen*=0.55; reasons.push("CV/speech focus without IR/NLP"); }
  let research=0; for(const m of CONCEPTS_RESEARCH) if(t.includes(m)) research++;
  const prodPresent=(dev.prod_t||0)>0.8;
  if(research>=2 && !prodPresent){ pen*=0.6; reasons.push("research-leaning, little production signal"); }
  return [pen, reasons]; }

// ---------------------------------------------------------------- integrity
function honeypotFlags(c){ const flags=[]; const yoeM=c.yoe*12;
  for(const h of c.career){ const sd=parseDate(h.start_date); const ed=parseDate(h.end_date)||TODAY;
    const dm=h.duration_months||0; if(!sd) continue;
    if(sd>TODAY) flags.push("future_start");
    const span=monthsBetween(sd,ed); if(dm-span>13) flags.push("tenure_impossible:"+(h.company||"?")); }
  let adv0=0; for(const s of c.skills) if((s.proficiency==="expert"||s.proficiency==="advanced")&&(s.duration_months||0)===0) adv0++;
  if(adv0>=4) flags.push("mastery_without_time:"+adv0);
  let total=0; for(const h of c.career) total+=(h.duration_months||0);
  if(total-yoeM>60) flags.push("career_exceeds_experience");
  return flags; }
function honeypotScore(c){ const flags=honeypotFlags(c); if(!flags.length) return [1.0,flags];
  const hard=flags.some(f=>f.startsWith("tenure_impossible")||f.startsWith("mastery_without_time")||f.startsWith("future_start"));
  return [hard?0.03:0.5, flags]; }
function stufferScore(c, titleScore){ let buzz=0; for(const s of c.skillSet) if(AI_BUZZ.has(s)) buzz++;
  if(titleScore>=0.5) return [1.0,false];
  const tell=CONCEPTS_TUTORIAL.some(t=>c.ctext.includes(t));
  if(titleScore<=0.1 && buzz>=3) return [tell?0.25:0.35, true];
  if(titleScore<0.4 && buzz>=5 && tell) return [0.4, true];
  return [1.0,false]; }

// ---------------------------------------------------------------- behavioural
function recencyFactor(la){ const d=parseDate(la); if(!d) return 0.8; const days=daysSince(d);
  if(days<=30) return 1.0; if(days<=90) return 0.96; if(days<=180) return 0.88; if(days<=365) return 0.72; return 0.55; }
function availabilityMultiplier(c){ const s=c.signals;
  const recency=recencyFactor(s.last_active_date);
  let resp=s.recruiter_response_rate; if(resp==null) resp=0;
  const respF=0.75+0.25*Math.min(resp/0.5,1);
  const openF=s.open_to_work_flag?1.0:0.92;
  const icr=s.interview_completion_rate||0; const icrF=0.92+0.08*Math.min(icr,1);
  const comp=(s.profile_completeness_score||0)/100; const compF=0.96+0.04*comp;
  const saved=s.saved_by_recruiters_30d||0; const demandF=1+0.05*Math.min(saved/5,1);
  let trust=0; if(s.verified_email) trust+=0.015; if(s.verified_phone) trust+=0.015; if(s.linkedin_connected) trust+=0.01;
  let mult=recency*respF*openF*icrF*compF*demandF*(1+trust);
  return Math.max(0.62, Math.min(1.08, mult)); }
function availabilityConcern(c){ const s=c.signals; const resp=s.recruiter_response_rate??1.0;
  const d=parseDate(s.last_active_date); const days=d?daysSince(d):999;
  if(days>180) return `inactive ~${Math.floor(days/30)} months`;
  if(resp<0.2) return `low recruiter response rate (${Math.round(resp*100)}%)`;
  const notice=s.notice_period_days||0; if(notice>=90) return `long notice period (${notice}d)`;
  return null; }

// ---------------------------------------------------------------- scoring
const W={title:0.22, domain:0.22, sem_main:0.11, sem_core:0.13, experience:0.10, career:0.14, location:0.08};
export function structuredComponents(c){
  const [t,tev]=titleFit(c); const [d,dev]=domainFit(c,t); const [e]=experienceFit(c);
  const [car,carev]=careerArc(c); const [loc]=locationFit(c);
  const [dqPen,dqReasons]=disqualifierPenalty(c,dev); const [hpMult,hpFlags]=honeypotScore(c);
  const [stMult,isStuffer]=stufferScore(c,t);
  return {title:t,domain:d,experience:e,career:car,location:loc,domain_ev:dev,
    dq_pen:dqPen,dq_reasons:dqReasons,hp_mult:hpMult,hp_flags:hpFlags,st_mult:stMult,is_stuffer:isStuffer}; }
export function combine(comp, semMain, semCore, semAnti, behav){
  let fit=W.title*comp.title+W.domain*comp.domain+W.sem_main*semMain+W.sem_core*semCore
    +W.experience*comp.experience+W.career*comp.career+W.location*comp.location;
  if(semAnti>0.62 && comp.title<0.4) fit*=0.85;
  const final=fit*behav*comp.dq_pen*comp.hp_mult*comp.st_mult;
  return {fit,final,title:comp.title,domain:comp.domain,experience:comp.experience,career:comp.career,
    location:comp.location,sem_main:semMain,sem_core:semCore,behav,dq_pen:comp.dq_pen,
    hp_mult:comp.hp_mult,st_mult:comp.st_mult}; }

// ---------------------------------------------------------------- reasoning
const EVIDENCE_DISPLAY=[["information retrieval","information retrieval"],["learning to rank","learning-to-rank"],
  ["ranking","ranking systems"],["recommendation","recommendation systems"],["recommender","recommender systems"],
  ["semantic search","semantic search"],["vector search","vector search"],["vector representation","vector representations"],
  ["search & discovery","search & discovery"],["search and discovery","search & discovery"],
  ["search infrastructure","search infrastructure"],["search backend","search backends"],
  ["embedding","embeddings"],["bm25","BM25 retrieval"],["text encoder","text encoders"],
  ["hybrid search","hybrid search"],["re-rank","re-ranking"],["personalization","personalization"]];
const SKILL_DISPLAY={"faiss":"FAISS","pinecone":"Pinecone","weaviate":"Weaviate","qdrant":"Qdrant",
  "milvus":"Milvus","pgvector":"pgvector","elasticsearch":"Elasticsearch","opensearch":"OpenSearch",
  "haystack":"Haystack","pytorch":"PyTorch","learning to rank":"Learning-to-Rank","bm25":"BM25",
  "qlora":"QLoRA","lora":"LoRA","peft":"PEFT","sentence transformers":"Sentence-Transformers","python":"Python"};
function foundEvidence(c, limit=2){ const seen=new Set(), out=[];
  for(const [needle,disp] of EVIDENCE_DISPLAY){ if(c.ctext.includes(needle)&&!seen.has(disp)){ out.push(disp); seen.add(disp);} if(out.length>=limit) break; }
  return out; }
function namedSkills(c, limit=3){ const out=[]; for(const s of c.skillList){ if(SKILL_DISPLAY[s]) out.push(SKILL_DISPLAY[s]); if(out.length>=limit) break; } return out; }
function companies(c, limit=2){ const out=[]; for(const h of c.career.slice(0,limit)){ if(h.company) out.push(h.company); } return out; }
export function makeReasoning(c, comp, score){
  const p=c.profile; const title=p.current_title||"Engineer"; const yoe=c.yoe;
  const loc=(p.location||"").split(",")[0].trim();
  const evidence=foundEvidence(c); const skills=namedSkills(c); const comps=companies(c);
  const concern=availabilityConcern(c);
  let lead=`${title} with ${yoe.toFixed(0)} yrs`; if(comps.length) lead+=` (${comps.slice(0,2).join(", ")})`;
  let fit; if(evidence.length) fit=`; direct ${evidence.join(", ")} experience`;
  else if(comp.domain>0.45) fit="; applied-ML / retrieval background";
  else if(comp.title>=0.85) fit="; core ML engineering profile";
  else fit="; adjacent engineering background";
  if(skills.length) fit+=` (${skills.join(", ")})`;
  let locc=""; if(comp.location>=0.9 && loc) locc=`; ${loc}-based`;
  else if(comp.location>=0.6 && loc) locc=c.signals.willing_to_relocate?`; ${loc}, open to relocate`:`; ${loc}`;
  const resp=c.signals.recruiter_response_rate; let tail;
  if(concern) tail=`. Concern: ${concern}.`;
  else if(resp!=null && resp>=0.5) tail=`. Engaged (responds to ${Math.round(resp*100)}% of recruiters).`;
  else tail=".";
  let text=lead+fit+locc+tail;
  if(score<0.45) text=text.replace(/\.+$/,"")+"; included as lower-confidence filler.";
  return text.replace(/\s+/g," ").trim().slice(0,300);
}

// ---------------------------------------------------------------- orchestration
const clip01=x=>Math.max(0,Math.min(1,x));
/* embFn: async (texts[]) => Float32Array[] normalized. */
export async function rankAll(rawList, embFn, progressCb){
  const cands=rawList.map(r=>new Candidate(r));
  // JD query vectors + candidate doc vectors
  const jdVecs=await embFn(JD_QUERIES);
  const docVecs=await embFn(cands.map(c=>semanticDocument(c)), progressCb);
  const dot=(a,b)=>{ let s=0; for(let i=0;i<a.length;i++) s+=a[i]*b[i]; return s; };
  const rows=cands.map((c,i)=>{
    const v=docVecs[i];
    const semMain=clip01((dot(v,jdVecs[0])+1)/2);
    const semCore=clip01((dot(v,jdVecs[1])+1)/2);
    const semAnti=clip01((dot(v,jdVecs[2])+1)/2);
    const comp=structuredComponents(c);
    const behav=availabilityMultiplier(c);
    const blend=combine(comp,semMain,semCore,semAnti,behav);
    return {cand:c, comp, blend};
  });
  rows.sort((a,b)=> (b.blend.final-a.blend.final) || (a.cand.id<b.cand.id?-1:1));
  return rows;
}
