import React, { useState, useEffect, useMemo, useRef } from "react";
import { Search, Plus, LayoutGrid, Table2, Download, RotateCcw, Trash2, Copy, X, ChevronDown, GripVertical } from "lucide-react";

const SEED = [{"no": 1, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Hammer Test: PVC vs SWR Pro (hero film)", "length": "90", "hook": "Dono pipe, ek hi hathoda — dekhte hain kaun tootta hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 2, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The Drop Test", "length": "90", "hook": "Dusri manzil se gira ke dekhte hain.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 3, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Slow-motion impact close-up", "length": "90", "hook": "Strike ka woh ek pal — slow motion mein.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 4, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“Maaro. Phir Uthao.” master format", "length": "90", "hook": "Pehle maaro. Strong nikle, tab uthao.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 5, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Load test — pipe under weight", "length": "90", "hook": "Itna bhaar daala — phir bhi intact.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 6, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Plumber’s first reaction (hammer)", "length": "90", "hook": "Plumber ne pehli baar maara — reaction dekhiye.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 7, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Blind test: guess which survives", "length": "90", "hook": "Bina dekhe batao — kaun bachega?", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 8, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "What “4X” actually means on site", "length": "90", "hook": "4X sunne mein accha — par site pe matlab kya?", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 9, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "3-layer PP cut-section animation", "length": "90", "hook": "Andar dekho — ek nahi, teen layer.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 10, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "PP vs PVC: 60-sec material science", "length": "90", "hook": "PP aur PVC mein farq sirf naam ka nahi.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 11, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“Purana PVC bhaari hai kyunki purana hai”", "length": "90", "hook": "Bhaari matlab premium nahi — bhaari matlab purana.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 12, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Inside the wall — layer by layer", "length": "90", "hook": "Har layer ka apna kaam hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 13, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "One man, 3 floors", "length": "90", "hook": "PVC: do aadmi. SWR Pro: ek haath, dasvi manzil.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 14, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Fitting race — install time-lapse", "length": "90", "hook": "Same kaam — kaun pehle khatam karta hai?", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 15, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Dealer math: more pipes per truck", "length": "90", "hook": "Ek hi truck, zyada maal — freight kam.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 16, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Less fatigue — a full day of lifting", "length": "90", "hook": "Din bhar uthao — kam thakaan.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 17, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“Strong jaisa, uthaane mein aasaan” payoff", "length": "90", "hook": "Strong dekha — ab uthaake dekho.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 18, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Site foreman POV after one job", "length": "90", "hook": "Ek project ke baad, meri team yahi maangti hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 19, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Architect POV: why material performance matters", "length": "90", "hook": "Aaj drainage ka decision material pe hai, aadat pe nahi.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 20, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "MEP consultant: Why SWR Pro is a paradigm Shift", "length": "90", "hook": "MEP consultant: Why SWR Pro is a paradigm Shift", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 21, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Services engineer on impact & long life", "length": "90", "hook": "Impact resistance ka matlab — lambi umar.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 22, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Consultant roundtable clip", "length": "90", "hook": "SWR category mein ab ek upgrade aa gaya.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 23, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Architect on affordable-housing drainage", "length": "90", "hook": "Affordable housing mein bhi sahi drainage.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 24, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Hospitality/commercial consultant — kitchens & labs", "length": "90", "hook": "Commercial kitchen aur lab — yahan material critical hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 25, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Sustainability angle — PP, recyclability, freight", "length": "90", "hook": "PP ka ek green pehlu bhi hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 26, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Senior plumber-trainer: “what I now teach”", "length": "90", "hook": "Apne juniors ko ab main yeh sikhata hoon.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 27, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Consultant Q&A: hot water & chemical resistance", "length": "90", "hook": "pH 2 se 12, aur garam paani — technically.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 28, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Consultant verdict: SWR Pro vs PVC (neutral tone)", "length": "90", "hook": "Neutral nazar se — dono ka farq.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 29, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Dealer counter script (customer asks PVC)", "length": "90", "hook": "Customer ne PVC maanga — maine kya bola?", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 30, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "5 reasons to switch", "length": "90", "hook": "Paanch wajah — PVC chhodne ki.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 31, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Almost-similar-price math", "length": "90", "hook": "Itne hi paise mein better — hisaab samjho.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 32, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Objection handling: “yeh halka hai”", "length": "90", "hook": "Jab customer bole ‘halka hai’ — yeh jawab do.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 33, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Distributor POV: why SWR PRO is boon", "length": "90", "hook": "Main apne retailers ko yeh kyun de raha hoon.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 34, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Retailer testimonial — first month", "length": "90", "hook": "Pehle mahine ka experience.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 35, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“Jab better option hai, toh PVC kyun?” film", "length": "90", "hook": "Seedha sawaal — PVC kyun?", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 36, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Shop-counter conversation (unscripted feel)", "length": "90", "hook": "Asli counter, asli baatcheet.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 37, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Dealer-to-dealer recommendation", "length": "90", "hook": "Ek dealer doosre dealer ko.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 38, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Affordable housing / 1–2 BHK fit", "length": "90", "hook": "1–2 BHK projects ke liye sahi choice.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 39, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Commercial kitchen drainage demo", "length": "90", "hook": "Commercial kitchen — garam paani, grease, sab.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 40, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Chemical lab — pH 2 to 12 use case", "length": "90", "hook": "Lab mein chemicals — pH 2 se 12 tak.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 41, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Service shafts & high-rise risers", "length": "90", "hook": "High-rise ke shaft mein kyun sahi.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 42, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "General residential drainage walkthrough", "length": "90", "hook": "Ghar ki poori drainage — ek walkthrough.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 43, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Product range & sizes (40–160 mm)", "length": "90", "hook": "40 se 160 mm — har size.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 44, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Portfolio: Silencio / Drain Pro / SWR Pro", "length": "90", "hook": "Teen products, teen zarooratein — kaunsa kahan.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 45, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Launch announcement film", "length": "90", "hook": "PVC SWR ka better replacement — aa gaya.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 46, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "UGC challenge invite", "length": "90", "hook": "Aap bhi maaro, phir uthao — tag karo.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 47, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Compilation: 10 plumbers hammer test", "length": "90", "hook": "Dus plumber. Ek test. Ek result.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 48, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“I switched” testimonial series", "length": "90", "hook": "Maine PVC chhoda — yeh meri wajah.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 49, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Behind-the-scenes: demo kit unboxing", "length": "90", "hook": "Network ko mila demo kit — andar kya hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 50, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Regional-language signature versions", "length": "90", "hook": "[Local language] mein — maaro, phir uthao.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 51, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Creators League leaderboard shout-out", "length": "90", "hook": "Is hafte ke top creators — aur inaam.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 52, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "“City by City” localised drop", "length": "90", "hook": "Ab [city] mein — SWR Pro.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 53, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "FAQ film — 5 questions everyone asks", "length": "90", "hook": "Paanch sawaal jo har koi poochta hai.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 54, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Final conversion anthem — movement recap", "length": "90", "hook": "Ab SWR mein better option hai — sab keh rahe hain.", "agency": "WRM", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 55, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Agarwal Sky Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "Published", "owner": "Vaibhav", "deadline": ""}, {"no": 56, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Chaitya- Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "Published", "owner": "Vaibhav", "deadline": ""}, {"no": 57, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "TW Wadhwa - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "Published", "owner": "Vaibhav", "deadline": ""}, {"no": 58, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Agarwal Foresta - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "Ready", "owner": "Vaibhav", "deadline": ""}, {"no": 59, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "GCC - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "Ready", "owner": "Vaibhav", "deadline": ""}, {"no": 60, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Swaminarayan QnA - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 61, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Runwal - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 62, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Interview - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 63, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Cidco 1 - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 64, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Cidco 2 - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 65, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Cidco 3 - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 66, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Cidco 4 - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 67, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Regency Inc, Palm Beach - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 68, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "One Akshar, Palm Beach", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 69, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Sanpada - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 70, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "Satyam Althra, Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 71, "brand": "Astral Pipes", "zone": "Project Case Study", "title": "One Luxuria, Kharkopar - Mumbai", "length": "90", "hook": "", "agency": "WRM", "status": "In Review", "owner": "Vaibhav", "deadline": ""}, {"no": 72, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why CPVC handles 93°C continuous, PVC fails at 60°C — polymer chain explained", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 73, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The pressure rating decline: how working pressure drops as temperature rises", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 74, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Pipe wall thickness vs OD: what SDR tells you in practice", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 75, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Crush resistance of DWC pipes: SN4, SN8, SN16 classes", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 76, "brand": "Astral Water Tanks", "zone": "NON-AI Product Video", "title": "What \"food-grade\" means in water tanks: heavy metal migration thresholds", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 77, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "PVC vs CPVC molecular structure: one Cl atom changes everything", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 78, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Tensile strength comparison in MPa: GI, CI, PVC, CPVC, PEX", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 79, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Chemical resistance: 100+ chemicals tested on Astral industrial pipes", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 80, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The 4-bar, 6-bar, 10-bar rating: what pressure class a home actually needs", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 81, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "CTS (Copper Tube Size) sizing system in CPVC PRO", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 82, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "IPS vs CTS sizing — not interchangeable, and here's why", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 83, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why long CPVC runs need expansion loops or offsets", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 84, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Solvent cement chemistry: how WELD-ON softens and re-bonds CPVC", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 85, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Cure time vs set time: the difference every plumber should know", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 86, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Solvent evaporation rate: why an opened cement can loses bond strength", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 87, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Biofilm growth: how interior smoothness reduces bacterial adhesion", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 88, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why GI pipes lose up to 30% bore diameter to scale in 10 years", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 89, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The pH range CPVC handles: 1 to 14 across most chemical families", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 90, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Oxygen permeability: why MultiPex's aluminium core matters in heating", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 91, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Thermal conductivity: CPVC at 0.14 W/m·K vs copper at 400 W/m·K", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 92, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Sound Transmission Class: how Silencio achieves <10 dB at 2 L/s flow", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 93, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "SWR pipe classifications: Type A vs Type B under IS 13592", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 94, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Fire Pro CPVC: Limiting Oxygen Index of 60 explained", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 95, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "IS 16088: India's CPVC fire sprinkler benchmark", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 96, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "uPVC pressure pipes for agriculture: PN 4, 6, 10, 12.5 explained", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 97, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Column pipe load calculation: pipe weight + water column + pump", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 98, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why OPVC has 2x strength at the same weight as uPVC", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 99, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Ball valve seat materials: PTFE vs EPDM — when each is used", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 100, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Solvent cement working time at 20°C vs 40°C", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 101, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Aluminium layer in PEX-AL-PEX: oxygen barrier and shape memory", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 102, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Pipe sleeves through walls: accommodating thermal expansion", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 103, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Pipe printing: batch number and standard mark — why both matter", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 104, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Certification marks decoded: IS, BIS, NSF, UL — what each covers", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 105, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Flattening test: how SWR pipes are checked for ovality", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 106, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Vicat softening test: the temperature at which load deforms a polymer", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 107, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Density float test: PP vs PE in a beaker", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 108, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The 3 most common solvent cement application mistakes", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 109, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "How to tell if a cement can has gone bad — colour and viscosity", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 110, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Cement shelf life: 2 years sealed, 3 months once opened", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 111, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Brush sizing: why too small a brush ruins joint strength", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 112, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why CPVC cement turns brown when over-aged", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 113, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Deburring the cut edge: a 10-second step that prevents leaks", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 114, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The \"twist & hold\" jointing technique demonstrated", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 115, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "The 90° cut: why ovality at the cut destroys the joint", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 116, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Marking insertion depth: the pencil line before jointing", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 117, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "CPVC installation in 45°C summer: working time considerations", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 118, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Cement application during monsoon: humidity and bond strength", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 119, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Minimum cure time before pressure testing", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 120, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "CPVC pressure test: 1.5x working pressure, 24-hour hold", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 121, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Threaded transitions: which tape to use where", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 122, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why over-tightening cracks a CPVC threaded fitting", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 123, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Brass insert transitions: the safe metal-to-plastic joint", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 124, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Concealed plumbing: leave 10mm clearance for thermal movement", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 125, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Wall chases: depth and width for CPVC routing inside the wall", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 126, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Pipe insulation in concealed hot-water runs", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 127, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Snake-route installation: managing thermal expansion with bends", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 128, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Long-radius vs short-radius elbows in drainage", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 129, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Why a 90° drainage bend should be two 45° bends", "length": "", "hook": "", "agency": "", "status": "Not Started", "owner": "", "deadline": ""}, {"no": 130, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Sheetal Trade Link - Dealer Testimonial Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "Published", "owner": "", "deadline": ""}, {"no": 131, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Sheetal Agency - Dealer Testimonial Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "Published", "owner": "", "deadline": ""}, {"no": 132, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Shreeji Hardware - Thaltej -Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}, {"no": 133, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Dharma Nandan Enterprise - Bopal - Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}, {"no": 134, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "National - Capital Agency - Raipur, Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}, {"no": 135, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Gokul Agency, Bodakdev, Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}, {"no": 136, "brand": "Astral Pipes", "zone": "Testimonial-Dealer", "title": "Mahavir Trading, Naroda, Ahmedabad", "length": "80 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}, {"no": 137, "brand": "Astral Pipes", "zone": "NON-AI Product Video", "title": "Borewell - New Video - Tracktor stunt and other with RJ Mit", "length": "90 Sec", "hook": "", "agency": "RJ Mit", "status": "In Production", "owner": "", "deadline": ""}];;

// ---- Configuration -------------------------------------------------------
const STAGES = ["Not Started", "Scripting", "In Production", "In Review", "Ready", "Published", "On Hold"];
const STAGE_META = {
  "Not Started":  { dot: "#9aa1ad", bar: "#c4c9d2", tint: "#f3f4f6" },
  "Scripting":    { dot: "#a855f7", bar: "#c084fc", tint: "#faf5ff" },
  "In Production":{ dot: "#2d7ff9", bar: "#69a4fb", tint: "#eff5ff" },
  "In Review":    { dot: "#f59e0b", bar: "#fbbf24", tint: "#fffaeb" },
  "Ready":        { dot: "#14b8a6", bar: "#5eead4", tint: "#f0fdfa" },
  "Published":    { dot: "#22a06b", bar: "#6cc79b", tint: "#f0fbf5" },
  "On Hold":      { dot: "#ef4444", bar: "#f59a9a", tint: "#fef2f2" },
};
const STORE_KEY = "astral_video_tracker_v1";

const uid = () => Math.random().toString(36).slice(2, 9);
const withIds = (rows) => rows.map((r) => ({ id: uid(), ...r }));

// ---- Small UI atoms ------------------------------------------------------
function Field({ value, onChange, type = "text", placeholder, mono, multiline }) {
  const [v, setV] = useState(value ?? "");
  useEffect(() => setV(value ?? ""), [value]);
  const commit = () => { if (v !== (value ?? "")) onChange(v); };
  const cls = "edit-field" + (mono ? " mono" : "");
  if (multiline)
    return <textarea className={cls} rows={2} value={v} placeholder={placeholder}
      onChange={(e) => setV(e.target.value)} onBlur={commit} />;
  return <input className={cls} type={type} value={v} placeholder={placeholder}
    onChange={(e) => setV(e.target.value)} onBlur={commit}
    onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()} />;
}

function Select({ value, options, onChange, render }) {
  return (
    <div className="sel-wrap">
      <select className="sel" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o} value={o}>{o || "—"}</option>)}
      </select>
      {render ? render(value) : null}
      <ChevronDown size={13} className="sel-chev" />
    </div>
  );
}

function StatusPill({ status }) {
  const m = STAGE_META[status] || STAGE_META["Not Started"];
  return (
    <span className="pill" style={{ background: m.tint, color: m.dot }}>
      <span className="pill-dot" style={{ background: m.dot }} />
      {status}
    </span>
  );
}

// ---- Card ----------------------------------------------------------------
function Card({ row, owners, agencies, onChange, onDelete, onDup, onDragStart, brands, zones }) {
  const [open, setOpen] = useState(false);
  const m = STAGE_META[row.status] || STAGE_META["Not Started"];
  return (
    <div className="card" draggable onDragStart={(e) => onDragStart(e, row.id)}>
      <div className="card-bar" style={{ background: m.bar }} />
      <div className="card-head">
        <span className="card-no mono">#{row.no}</span>
        <span className="card-zone">{row.zone}</span>
        <div className="card-grip"><GripVertical size={13} /></div>
      </div>
      <Field value={row.title} onChange={(v) => onChange(row.id, "title", v)} placeholder="Untitled video" multiline />
      {row.hook && !open ? <p className="card-hook">{row.hook}</p> : null}
      <div className="card-meta">
        <StatusPill status={row.status} />
        {row.agency ? <span className="chip">{row.agency}</span> : null}
        {row.length ? <span className="chip ghost mono">{row.length}{/^\d+$/.test(row.length) ? "s" : ""}</span> : null}
      </div>
      <button className="card-expand" onClick={() => setOpen(!open)}>
        {open ? "Hide details" : "Edit details"}<ChevronDown size={12} style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      {open && (
        <div className="card-edit">
          <label>Status<Select value={row.status} options={STAGES} onChange={(v) => onChange(row.id, "status", v)} /></label>
          <label>Brand<Select value={row.brand} options={brands} onChange={(v) => onChange(row.id, "brand", v)} /></label>
          <label>Zone<Select value={row.zone} options={zones} onChange={(v) => onChange(row.id, "zone", v)} /></label>
          <label>Agency<Select value={row.agency} options={agencies} onChange={(v) => onChange(row.id, "agency", v)} /></label>
          <label>Owner<Select value={row.owner} options={owners} onChange={(v) => onChange(row.id, "owner", v)} /></label>
          <label>Length<Field value={row.length} mono onChange={(v) => onChange(row.id, "length", v)} placeholder="90" /></label>
          <label>Deadline<Field value={row.deadline} type="date" mono onChange={(v) => onChange(row.id, "deadline", v)} /></label>
          <label className="wide">Hook / subject<Field value={row.hook} onChange={(v) => onChange(row.id, "hook", v)} placeholder="Opening line…" multiline /></label>
          <div className="card-actions">
            <button onClick={() => onDup(row.id)}><Copy size={13} /> Duplicate</button>
            <button className="danger" onClick={() => onDelete(row.id)}><Trash2 size={13} /> Delete</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Board ---------------------------------------------------------------
function Board({ rows, ...handlers }) {
  const [over, setOver] = useState(null);
  const drag = useRef(null);
  const onDragStart = (e, id) => { drag.current = id; e.dataTransfer.effectAllowed = "move"; };
  const onDrop = (stage) => { if (drag.current) handlers.onChange(drag.current, "status", stage); drag.current = null; setOver(null); };
  return (
    <div className="board">
      {STAGES.map((stage) => {
        const items = rows.filter((r) => r.status === stage);
        const m = STAGE_META[stage];
        return (
          <div key={stage} className={"col" + (over === stage ? " over" : "")}
            onDragOver={(e) => { e.preventDefault(); setOver(stage); }}
            onDragLeave={() => setOver((o) => (o === stage ? null : o))}
            onDrop={() => onDrop(stage)}>
            <div className="col-head">
              <span className="col-dot" style={{ background: m.dot }} />
              <span className="col-name">{stage}</span>
              <span className="col-count mono">{items.length}</span>
            </div>
            <div className="col-body">
              {items.map((r) => <Card key={r.id} row={r} onDragStart={onDragStart} {...handlers} />)}
              <button className="col-add" onClick={() => handlers.onAdd(stage)}><Plus size={13} /> Add</button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---- Table ---------------------------------------------------------------
function TableView({ rows, owners, agencies, brands, zones, onChange, onDelete }) {
  return (
    <div className="tablewrap">
      <table className="tbl">
        <thead><tr>
          <th className="mono">#</th><th>Title</th><th>Brand</th><th>Zone</th>
          <th>Agency</th><th>Owner</th><th>Status</th><th>Len</th><th>Deadline</th><th></th>
        </tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td className="mono dim">{r.no}</td>
              <td className="t-title"><Field value={r.title} onChange={(v) => onChange(r.id, "title", v)} /></td>
              <td><Select value={r.brand} options={brands} onChange={(v) => onChange(r.id, "brand", v)} /></td>
              <td><Select value={r.zone} options={zones} onChange={(v) => onChange(r.id, "zone", v)} /></td>
              <td><Select value={r.agency} options={agencies} onChange={(v) => onChange(r.id, "agency", v)} /></td>
              <td><Select value={r.owner} options={owners} onChange={(v) => onChange(r.id, "owner", v)} /></td>
              <td><Select value={r.status} options={STAGES} onChange={(v) => onChange(r.id, "status", v)} render={(s) => <StatusPill status={s} />} /></td>
              <td className="mono"><Field value={r.length} mono onChange={(v) => onChange(r.id, "length", v)} /></td>
              <td className="mono"><Field value={r.deadline} type="date" mono onChange={(v) => onChange(r.id, "deadline", v)} /></td>
              <td><button className="row-del" onClick={() => onDelete(r.id)}><Trash2 size={14} /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---- App -----------------------------------------------------------------
export default function App() {
  const [rows, setRows] = useState(null);
  const [view, setView] = useState("board");
  const [q, setQ] = useState("");
  const [fBrand, setFBrand] = useState("All");
  const [fZone, setFZone] = useState("All");
  const [fAgency, setFAgency] = useState("All");
  const [fStatus, setFStatus] = useState("All");

  // load
  useEffect(() => {
    (async () => {
      try {
        const r = await window.storage?.get(STORE_KEY);
        if (r?.value) { setRows(JSON.parse(r.value)); return; }
      } catch (e) {}
      setRows(withIds(SEED));
    })();
  }, []);
  // save
  useEffect(() => {
    if (!rows) return;
    (async () => { try { await window.storage?.set(STORE_KEY, JSON.stringify(rows)); } catch (e) {} })();
  }, [rows]);

  const opts = useMemo(() => {
    const u = (k) => Array.from(new Set((rows || []).map((r) => r[k]).filter(Boolean))).sort();
    return {
      brands: u("brand").length ? u("brand") : ["Astral Pipes"],
      zones: u("zone"),
      agencies: ["", ...u("agency").filter(Boolean)],
      owners: ["", ...u("owner").filter(Boolean)],
    };
  }, [rows]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const ql = q.toLowerCase();
    return rows.filter((r) =>
      (fBrand === "All" || r.brand === fBrand) &&
      (fZone === "All" || r.zone === fZone) &&
      (fAgency === "All" || r.agency === fAgency) &&
      (fStatus === "All" || r.status === fStatus) &&
      (!ql || [r.title, r.hook, r.owner, r.zone].some((x) => (x || "").toLowerCase().includes(ql)))
    );
  }, [rows, q, fBrand, fZone, fAgency, fStatus]);

  const stats = useMemo(() => {
    const base = rows || [];
    const done = base.filter((r) => r.status === "Published").length;
    const active = base.filter((r) => ["Scripting", "In Production", "In Review", "Ready"].includes(r.status)).length;
    return { total: base.length, done, active, todo: base.filter((r) => r.status === "Not Started").length };
  }, [rows]);

  // mutations
  const change = (id, k, v) => setRows((rs) => rs.map((r) => (r.id === id ? { ...r, [k]: v } : r)));
  const del = (id) => setRows((rs) => rs.filter((r) => r.id !== id));
  const dup = (id) => setRows((rs) => {
    const i = rs.findIndex((r) => r.id === id); const c = { ...rs[i], id: uid(), title: rs[i].title + " (copy)" };
    return [...rs.slice(0, i + 1), c, ...rs.slice(i + 1)];
  });
  const add = (stage = "Not Started") => setRows((rs) => {
    const nextNo = Math.max(0, ...rs.map((r) => Number(r.no) || 0)) + 1;
    return [{ id: uid(), no: nextNo, brand: fBrand !== "All" ? fBrand : (opts.brands[0] || "Astral Pipes"),
      zone: fZone !== "All" ? fZone : (opts.zones[0] || "NON-AI Product Video"), title: "", length: "", hook: "",
      agency: "", status: stage, owner: "", deadline: "" }, ...rs];
  });
  const reset = () => { if (confirm("Reset to the original 137 videos? Your edits will be lost.")) setRows(withIds(SEED)); };
  const exportCsv = () => {
    const cols = ["no", "brand", "zone", "title", "length", "hook", "agency", "status", "owner", "deadline"];
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "astral_video_tracker.csv"; a.click();
  };

  if (!rows) return <div className="app"><div className="loading mono">Loading tracker…</div></div>;

  const handlers = { onChange: change, onDelete: del, onDup: dup, onAdd: add,
    owners: opts.owners, agencies: opts.agencies, brands: opts.brands, zones: opts.zones };

  return (
    <div className="app">
      <Styles />
      <header className="top">
        <div className="brandblock">
          <div className="logo">ASTRAL</div>
          <div className="titles">
            <h1>Video Content Tracker</h1>
            <p>Pipes · Water Tanks · Foundation — one row per video, live across the production pipeline.</p>
          </div>
        </div>
        <div className="stat-strip">
          <Stat n={stats.total} l="Total" />
          <Stat n={stats.todo} l="Not started" />
          <Stat n={stats.active} l="In pipeline" accent="#2d7ff9" />
          <Stat n={stats.done} l="Published" accent="#22a06b" />
        </div>
      </header>

      <div className="toolbar">
        <div className="search">
          <Search size={15} />
          <input placeholder="Search titles, hooks, owners…" value={q} onChange={(e) => setQ(e.target.value)} />
          {q && <button onClick={() => setQ("")}><X size={14} /></button>}
        </div>
        <Filter label="Brand" value={fBrand} set={setFBrand} options={opts.brands} />
        <Filter label="Zone" value={fZone} set={setFZone} options={opts.zones} />
        <Filter label="Agency" value={fAgency} set={setFAgency} options={opts.agencies.filter(Boolean)} />
        <Filter label="Status" value={fStatus} set={setFStatus} options={STAGES} />
        <div className="spacer" />
        <div className="viewtoggle">
          <button className={view === "board" ? "on" : ""} onClick={() => setView("board")}><LayoutGrid size={15} /> Board</button>
          <button className={view === "table" ? "on" : ""} onClick={() => setView("table")}><Table2 size={15} /> Table</button>
        </div>
        <button className="btn" onClick={() => add()}><Plus size={15} /> New</button>
        <button className="btn ghost" onClick={exportCsv}><Download size={15} /> CSV</button>
        <button className="btn ghost" onClick={reset} title="Reset to original"><RotateCcw size={15} /></button>
      </div>

      <div className="count-line mono">
        Showing {filtered.length} of {rows.length}
        {(fBrand !== "All" || fZone !== "All" || fAgency !== "All" || fStatus !== "All" || q) &&
          <button className="clearall" onClick={() => { setQ(""); setFBrand("All"); setFZone("All"); setFAgency("All"); setFStatus("All"); }}>clear filters</button>}
      </div>

      {view === "board"
        ? <Board rows={filtered} {...handlers} />
        : <TableView rows={filtered} {...handlers} />}
    </div>
  );
}

function Stat({ n, l, accent }) {
  return <div className="stat"><span className="stat-n mono" style={accent ? { color: accent } : {}}>{n}</span><span className="stat-l">{l}</span></div>;
}
function Filter({ label, value, set, options }) {
  return (
    <div className="filter">
      <select value={value} onChange={(e) => set(e.target.value)}>
        <option value="All">{label}: All</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <ChevronDown size={13} />
    </div>
  );
}

function Styles() {
  return <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;450;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    * { box-sizing: border-box; }
    .app {
      --ink:#15181f; --ink2:#3c424e; --dim:#828a98; --line:#e7e9ee; --line2:#eef0f4;
      --paper:#fbfbf9; --surface:#ffffff; --blue:#1b4d7e; --signal:#2d7ff9;
      font-family:'Inter',system-ui,sans-serif; color:var(--ink); background:var(--paper);
      min-height:100vh; padding:22px 26px 60px; -webkit-font-smoothing:antialiased;
    }
    .loading{padding:80px;text-align:center;color:var(--dim);}
    .mono{font-family:'JetBrains Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums;}

    /* header */
    .top{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;flex-wrap:wrap;
      padding-bottom:20px;border-bottom:1px solid var(--line);}
    .brandblock{display:flex;gap:16px;align-items:center;}
    .logo{font-family:'Space Grotesk',sans-serif;font-weight:700;letter-spacing:.22em;font-size:13px;
      color:#fff;background:var(--blue);padding:9px 11px;border-radius:7px;align-self:flex-start;
      box-shadow:0 1px 0 rgba(0,0,0,.04);}
    .titles h1{font-family:'Space Grotesk',sans-serif;font-size:23px;font-weight:600;margin:0;letter-spacing:-.01em;}
    .titles p{margin:3px 0 0;color:var(--dim);font-size:13px;max-width:46ch;}
    .stat-strip{display:flex;gap:8px;}
    .stat{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:10px 15px;min-width:78px;
      display:flex;flex-direction:column;gap:2px;}
    .stat-n{font-family:'Space Grotesk',sans-serif;font-size:25px;font-weight:600;line-height:1;letter-spacing:-.02em;}
    .stat-l{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em;}

    /* toolbar */
    .toolbar{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:18px 0 6px;}
    .search{display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--line);
      border-radius:9px;padding:0 11px;min-width:230px;flex:0 1 280px;color:var(--dim);}
    .search input{border:0;outline:0;background:transparent;padding:9px 0;font-size:13.5px;width:100%;color:var(--ink);font-family:inherit;}
    .search button{border:0;background:none;color:var(--dim);cursor:pointer;display:flex;padding:2px;}
    .filter{position:relative;display:flex;align-items:center;}
    .filter select{appearance:none;border:1px solid var(--line);background:var(--surface);border-radius:9px;
      padding:9px 28px 9px 11px;font-size:13px;color:var(--ink2);cursor:pointer;font-family:inherit;font-weight:500;}
    .filter svg{position:absolute;right:9px;color:var(--dim);pointer-events:none;}
    .filter select:hover{border-color:#d7dae1;}
    .spacer{flex:1;}
    .viewtoggle{display:flex;background:var(--line2);border-radius:9px;padding:3px;gap:2px;}
    .viewtoggle button{display:flex;align-items:center;gap:6px;border:0;background:none;padding:6px 12px;border-radius:7px;
      font-size:13px;color:var(--ink2);cursor:pointer;font-weight:500;font-family:inherit;}
    .viewtoggle button.on{background:var(--surface);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.07);}
    .btn{display:flex;align-items:center;gap:6px;border:1px solid var(--blue);background:var(--blue);color:#fff;
      padding:9px 14px;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;}
    .btn:hover{background:#16406a;}
    .btn.ghost{background:var(--surface);color:var(--ink2);border-color:var(--line);}
    .btn.ghost:hover{border-color:#d7dae1;color:var(--ink);}

    .count-line{font-size:12px;color:var(--dim);margin:8px 2px 16px;display:flex;align-items:center;gap:12px;}
    .clearall{border:0;background:none;color:var(--signal);cursor:pointer;font-size:12px;font-family:inherit;text-decoration:underline;}

    /* board */
    .board{display:flex;gap:14px;overflow-x:auto;padding-bottom:14px;align-items:flex-start;}
    .col{flex:0 0 268px;background:var(--line2);border-radius:13px;padding:5px;transition:background .15s,box-shadow .15s;}
    .col.over{background:#e3edfb;box-shadow:inset 0 0 0 1.5px var(--signal);}
    .col-head{display:flex;align-items:center;gap:8px;padding:11px 10px 9px;}
    .col-dot{width:8px;height:8px;border-radius:50%;flex:none;}
    .col-name{font-size:12.5px;font-weight:600;color:var(--ink2);letter-spacing:.01em;}
    .col-count{margin-left:auto;font-size:12px;color:var(--dim);background:var(--surface);border-radius:20px;padding:1px 9px;}
    .col-body{display:flex;flex-direction:column;gap:8px;padding:2px;max-height:none;}
    .col-add{display:flex;align-items:center;justify-content:center;gap:5px;border:1px dashed #cfd4dd;background:none;
      color:var(--dim);padding:8px;border-radius:9px;font-size:12.5px;cursor:pointer;font-family:inherit;}
    .col-add:hover{border-color:var(--signal);color:var(--signal);}

    /* card */
    .card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:11px;
      padding:11px 12px 10px;overflow:hidden;cursor:default;box-shadow:0 1px 2px rgba(20,24,31,.03);}
    .card:hover{border-color:#d7dae1;box-shadow:0 3px 10px rgba(20,24,31,.06);}
    .card-bar{position:absolute;left:0;top:0;bottom:0;width:3px;}
    .card-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;}
    .card-no{font-size:11px;color:var(--dim);font-weight:500;}
    .card-zone{font-size:10.5px;color:var(--blue);background:#eef3f8;padding:2px 7px;border-radius:5px;font-weight:500;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;}
    .card-grip{margin-left:auto;color:#c3c8d1;cursor:grab;display:flex;}
    .card-hook{font-size:12px;color:var(--dim);margin:5px 0 0;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
    .card-meta{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:9px;}
    .chip{font-size:11px;color:var(--ink2);background:#f2f4f7;padding:2px 8px;border-radius:5px;font-weight:500;}
    .chip.ghost{background:none;border:1px solid var(--line);color:var(--dim);}
    .card-expand{display:flex;align-items:center;gap:4px;border:0;background:none;color:var(--dim);font-size:11.5px;
      cursor:pointer;padding:8px 0 1px;font-family:inherit;}
    .card-expand:hover{color:var(--signal);}
    .card-expand svg{transition:transform .15s;}
    .card-edit{display:grid;grid-template-columns:1fr 1fr;gap:9px 10px;margin-top:9px;padding-top:11px;border-top:1px solid var(--line2);}
    .card-edit label{display:flex;flex-direction:column;gap:3px;font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.04em;font-weight:500;}
    .card-edit label.wide{grid-column:1/3;}
    .card-actions{grid-column:1/3;display:flex;gap:8px;margin-top:2px;}
    .card-actions button{display:flex;align-items:center;gap:5px;border:1px solid var(--line);background:var(--surface);
      color:var(--ink2);padding:6px 10px;border-radius:7px;font-size:12px;cursor:pointer;font-family:inherit;font-weight:500;}
    .card-actions button:hover{border-color:#d7dae1;}
    .card-actions .danger{color:#d23f3f;}
    .card-actions .danger:hover{background:#fef2f2;border-color:#f3c9c9;}

    /* edit fields */
    .edit-field{border:1px solid transparent;background:transparent;border-radius:6px;padding:5px 7px;font-size:13px;
      font-family:inherit;color:var(--ink);width:100%;resize:none;line-height:1.4;}
    .card > .edit-field{font-family:'Space Grotesk',sans-serif;font-weight:500;font-size:13.5px;padding:3px 5px;margin-left:-5px;}
    .edit-field:hover{background:#f5f6f8;}
    .edit-field:focus{outline:0;background:#fff;border-color:var(--signal);box-shadow:0 0 0 3px rgba(45,127,249,.12);}
    .edit-field.mono{font-family:'JetBrains Mono',monospace;font-size:12px;}

    /* select atom (inline editors) */
    .sel-wrap{position:relative;display:flex;align-items:center;}
    .sel{appearance:none;border:1px solid transparent;background:transparent;border-radius:6px;padding:5px 22px 5px 7px;
      font-size:12.5px;font-family:inherit;color:var(--ink);cursor:pointer;width:100%;font-weight:500;}
    .sel:hover{background:#f5f6f8;}
    .sel:focus{outline:0;background:#fff;border-color:var(--signal);box-shadow:0 0 0 3px rgba(45,127,249,.12);}
    .sel-chev{position:absolute;right:6px;color:var(--dim);pointer-events:none;}
    .card-edit .sel{border:1px solid var(--line);background:var(--surface);}

    /* pill */
    .pill{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;padding:2px 9px 2px 7px;border-radius:20px;white-space:nowrap;}
    .pill-dot{width:6px;height:6px;border-radius:50%;}

    /* table */
    .tablewrap{border:1px solid var(--line);border-radius:13px;overflow:auto;background:var(--surface);}
    .tbl{width:100%;border-collapse:collapse;font-size:13px;min-width:1000px;}
    .tbl thead th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);
      font-weight:600;padding:11px 12px;border-bottom:1px solid var(--line);background:#fcfcfb;position:sticky;top:0;}
    .tbl tbody td{padding:3px 6px;border-bottom:1px solid var(--line2);vertical-align:middle;}
    .tbl tbody tr:hover{background:#fcfcfa;}
    .tbl tbody tr:last-child td{border-bottom:0;}
    td.dim{color:var(--dim);padding-left:14px;}
    .t-title{min-width:280px;}
    .t-title .edit-field{font-weight:500;}
    .row-del{border:0;background:none;color:#c3c8d1;cursor:pointer;padding:6px;display:flex;border-radius:6px;}
    .row-del:hover{color:#d23f3f;background:#fef2f2;}

    @media (max-width:720px){
      .app{padding:16px 14px 50px;}
      .stat-strip{width:100%;}.stat{flex:1;min-width:0;}
      .titles p{display:none;}
    }
  `}</style>;
}
