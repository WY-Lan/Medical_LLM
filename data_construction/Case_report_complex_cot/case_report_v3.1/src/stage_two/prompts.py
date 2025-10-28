#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage Two Prompts: 定义第二阶段使用的提示模板
优化版本：添加更严格的内容判断模板
"""

Prompts = """
hello
"""

# 用于确认章节是否为案例部分的提示模板 - 更严格的版本
CASE_SECTION_CONFIRMATION_TEMPLATE = """
You are a medical literature analyst specialized in identifying detailed clinical case reports in medical journals. 
Your task is to analyze the provided section with EXTREME STRICTNESS to determine if it represents a genuine clinical case with specific patient data.
Section title: '{title}'

Section content sample: '{content_sample}'

CRITICAL REQUIREMENT: Be EXTREMELY STRICT in your evaluation. Only confirm as a clinical case if there is CLEAR, SPECIFIC and DETAILED patient data present.

A valid clinical case section MUST have AT LEAST THREE of these critical elements:
- Specific patient demographic information (exact age, gender, ethnicity)
- Detailed patient-specific medical history with clear temporal markers
- Explicit patient-specific symptoms or complaints with onset timing and progression
- Concrete examination findings directly linked to the specific patient
- Precise quantitative test results with values and units for the specific patient
- Clear treatment details (medications with dosages, procedures) applied to the specific patient

Additionally, the content MUST:
- Focus on a SINGLE patient case (not multiple patients or summarized cases)
- Contain SPECIFIC details rather than general descriptions
- Include TEMPORAL information about the patient's condition
- Present CONCRETE clinical findings rather than theoretical discussions

Consider these indicators of genuine clinical case sections:
- First-person descriptions of clinical reasoning for a specific patient
- Chronological narrative of a patient's clinical course with clear time references
- Detailed examination findings and test results with specific values
- Language indicating a specific patient case (e.g., 'A 65-year-old male presented with...')
- Logical progression from symptoms to examination to diagnosis specific to one patient

Examples of text that IS a clinical case:
- "A 42-year-old female presented with a 3-month history of progressive dyspnea and fatigue. Her past medical history included hypertension treated with lisinopril 10mg daily."
- "The patient, a 67-year-old male with a 20-year history of hypertension, experienced sudden chest pain and was admitted to the emergency department. Physical examination revealed BP of 165/95 mmHg and irregular heart rhythm."
- "A 35-year-old pregnant woman (G2P1) at 32 weeks gestation presented with severe epigastric pain and hypertension (160/100 mmHg). Laboratory tests showed elevated liver enzymes (ALT 150 U/L, AST 165 U/L) and low platelet count (95,000/μL)."

Examples of text that is NOT a clinical case:
- "Patients with hypertension often present with headache, dizziness, and blurred vision."
- "We reviewed 45 cases of rare lymphomas treated at our institution between 2010 and 2020."
- "The standard treatment for this condition includes ACE inhibitors and dietary modifications."
- "Table 1 shows the demographic characteristics of the study population."
- "Literature suggests that early intervention improves outcomes in these cases."
- "Several studies have demonstrated the efficacy of this approach in managing the disease."
- "A retrospective analysis was conducted on 120 patients who underwent the procedure."

If this is a clinical case with SPECIFIC, DETAILED PATIENT DATA meeting at least THREE of the critical elements listed above, respond with 'YES' followed by a brief explanation identifying the specific patient elements present.
Otherwise, respond with 'NO'. Be extremely cautious about confirming general discussions, literature reviews, or multiple-patient reports as clinical cases.
"""

# 无标题文本案例内容判断提示模板
CONTENT_ONLY_CASE_CONFIRMATION_TEMPLATE = """
You are a medical literature analyst specialized in determining if a text extract contains specific clinical case information.
Analyze the following text extract (without a title) with EXTREME STRICTNESS to determine if it contains detailed clinical case information about a specific patient.

Text content:
---------------
{content_sample}
---------------

CRITICAL REQUIREMENTS:
1. The text MUST contain SPECIFIC PATIENT DETAILS, not general medical information
2. It should describe a SINGLE PATIENT'S case, not multiple patients or general disease descriptions
3. The information MUST be CONCRETE and DETAILED enough to constitute a proper case report

A valid clinical case MUST have AT LEAST THREE of these elements:
- Specific demographic details (age, gender, ethnicity of a specific patient)
- Patient-specific medical history with clear temporal indicators
- Detailed patient-specific symptoms with onset and progression
- Concrete examination findings directly linked to the patient
- Specific test results with values for the patient
- Detailed treatment information applied to the specific patient

Text that IS a clinical case typically:
- Contains specific details about a real patient
- Has temporal markers (e.g., "After 2 months of treatment...")
- Contains exact measurements/values
- Describes a logical clinical progression for a specific patient

Text that is NOT a clinical case typically:
- Discusses general medical knowledge
- Reviews or summarizes multiple cases
- Describes general treatment approaches
- Discusses research methods or study designs
- Contains primarily theoretical discussions

Answer ONLY 'YES' if the text clearly contains specific clinical case information meeting at least 3 criteria.
Answer 'NO' for general medical discussions, literature reviews, or multiple-patient reports.
"""

# 新增: 更严格的案例内容判断模板，用于内容匹配
STRICT_CASE_CONTENT_TEMPLATE = """
You are a clinical case verification specialist with expertise in clinical data extraction and validation. 
Your task is to perform an EXTREMELY STRICT analysis of this text content to determine if it contains SPECIFIC PATIENT INFORMATION about a SINGLE CASE.

Text content to analyze:
---------------
{content}
---------------

MANDATORY REQUIREMENTS for a valid clinical case:
The text MUST contain AT LEAST THREE of the following elements to qualify as a clinical case:
1. Specific demographic information (EXACT age, gender)
2. Detailed medical history specific to a single patient
3. Clear description of the patient's presenting symptoms with temporal markers
4. Specific physical examination findings
5. Laboratory or imaging results with actual values/observations
6. Specific treatments administered to the patient

EXAMPLES of text that IS a clinical case:
- "We present a 66-year-old male with a past medical history of hypertension, peripheral arterial disease, and polio in childhood with residual left lower extremity weakness. At 58 years, the patient started falling due to increasing weakness in both his legs. His symptoms continued to progress and involved his upper extremities soon later."
- "A 43-year-old woman presented with right upper quadrant abdominal pain of 2 days' duration. Her laboratory results showed elevated liver enzymes: AST 345 U/L, ALT 298 U/L."

EXAMPLES of text that is NOT a clinical case:
- "Liver injury can result from various medications and toxins. Patients typically present with elevated liver enzymes."
- "Treatment options for this condition include surgical resection or conservative management with close monitoring."
- "We reviewed the clinical outcomes of 25 patients who underwent this procedure."

IMPORTANT: Be EXTREMELY STRICT. If there is ANY DOUBT about whether the content describes a specific clinical case with individual patient details, you MUST answer "NO".

Provide ONLY "YES" or "NO" as your answer, with no explanation or additional text.
"""

# 新增: 严格的讨论章节判断模板，用于内容匹配
STRICT_DISCUSSION_CONTENT_TEMPLATE = """
You are a medical literature specialist with expertise in analyzing clinical paper structures.
Your task is to perform an EXTREMELY STRICT analysis of this text content to determine if it represents a DISCUSSION section of a clinical case report.

Section title: '{title}'

Text content to analyze:
---------------
{content_sample}
---------------

MANDATORY REQUIREMENTS for a valid discussion section:
The text MUST show AT LEAST THREE of the following characteristics:
1. Analysis or interpretation of the presented case findings
2. Comparison with existing literature or similar cases
3. Reference to scientific evidence, studies, or citations
4. Discussion of pathophysiological mechanisms
5. Consideration of differential diagnoses or diagnostic challenges
6. Examination of treatment options, efficacy, or clinical outcomes
7. Broader context placement of the case or implications for clinical practice

Additionally, consider the section title: Some common discussion section titles include "Discussion", 
"Commentary", "Review", "Analysis", "Conclusion", or phrases containing these words.
However, the content is more important than the title.

EXAMPLES of text that IS a discussion section:
- "Chlorophenoxy herbicides are used widely for the control of broad-leaved weeds. MCPA is one of the major varieties of chlorophenoxy herbicides, and it is the most common cause of chlorophenoxy poisoning in the North Central Province of Sri Lanka. There is limited information on clinical toxicity from MCPA poisoning, with only six single case reports in the literature."
- "Our patient's presentation is consistent with previously reported cases of this syndrome. Smith et al. described similar findings in their series of 12 patients, noting that early intervention was associated with improved outcomes."

EXAMPLES of text that is NOT a discussion section:
- "A 58-year-old man presented to our emergency department with severe chest pain radiating to his left arm."
- "Physical examination revealed tachycardia (heart rate 110 bpm) and blood pressure of 160/95 mmHg."
- "The patient was started on aspirin 325mg and clopidogrel 75mg daily."
- "Materials and methods: We conducted a retrospective review of medical records from 2010-2020."

IMPORTANT: Be EXTREMELY STRICT. The text should primarily focus on interpreting findings, comparing with literature, or discussing mechanisms - not merely describing the patient or procedures performed.

Provide ONLY "YES" or "NO" as your answer, with no explanation or additional text.
"""

# 用于提取病例基本信息和检查信息的提示模板
CASE_INFO_EXTRACTION_TEMPLATE = """
You are a medical information extraction specialist tasked with precisely extracting structured data from clinical case reports. 
Extract the following information from this clinical case report with high accuracy. 
Do not add any information that is not explicitly stated in the text. 
Maintain the original clinical terminology and wording where possible.

CASE CONTENT: {case_content}

1. BASIC_INFO: Extract only the patient's basic information such as:
   - Demographic details (age, gender, ethnicity if mentioned)
   - Chief complaints and presenting symptoms
   - Duration and progression of symptoms
   - Relevant past medical history, family history, social history
   - Risk factors mentioned
   Do NOT include any diagnosis results, treatment plans, or examination results in this section.

2. EXAMINATION:
   a. EXAM_ITEMS: List all examination procedures performed, including:
      - Laboratory tests (blood tests, urinalysis, etc.)
      - Imaging studies (X-ray, CT, MRI, ultrasound, etc.)
      - Special diagnostic procedures (biopsies, endoscopies, etc.)
      - Physical examination findings
      - Be specific about exact tests when mentioned (e.g., 'CBC, liver function tests' not just 'blood tests')

   b. EXAM_RESULTS: List all examination results with their values and reference ranges when provided:
      - Abnormal and normal findings
      - Imaging observations
      - Pathology results
      - Laboratory values with units when mentioned

Format your response as a valid JSON object with the following structure, and nothing else:
{{
  "basic_info": "extracted text here",
  "examination": {{
    "exam_items": "extracted text here",
    "exam_results": "extracted text here"
  }}
}}
"""

# 用于从病例内容和讨论中提取诊断信息的提示模板
DIAGNOSIS_EXTRACTION_TEMPLATE = """
You are a medical diagnostic expert with expertise in analyzing clinical case reports. 
Extract ONLY the PRIMARY DIAGNOSIS from the following clinical case and discussion.
Focus on the FINAL and DEFINITIVE diagnosis, not differential or provisional diagnoses.

CASE CONTENT: {case_content}

DISCUSSION: {discussion_content}

INSTRUCTIONS:
1. Extract ONLY the main, final diagnosis of the patient
2. Be precise and concise - just the condition name, not explanations
3. Use the exact terminology as presented in the text
4. If multiple diagnoses are present, focus only on the primary/main diagnosis
5. Do not include:
   - Differential diagnoses that were ruled out
   - Symptoms or clinical findings
   - Staging or classification details
   - Treatment information
   - Diagnostic procedures
   - Prognosis information

Format your response as a valid JSON with a single key 'diagnosis' and nothing else:
{{
  "diagnosis": "final diagnosis name"
}}

Example responses:
{{
  "diagnosis": "Acute myeloid leukemia"
}}

{{
  "diagnosis": "Severe aortic valve stenosis"
}}
"""

# 用于提取治疗项目列表的模板 - 优化版本
TREATMENT_ITEMS_EXTRACTION_TEMPLATE = """
You are a medical treatment specialist tasked with extracting a precise list of all treatment interventions from medical case reports.
Your task is to identify ONLY specific treatment procedures, medications, and interventions that were ACTUALLY ADMINISTERED to the patient.

CONTENT:
{case_content}

EXTRACTION REQUIREMENTS:
1. Extract ONLY concrete treatment interventions that were definitively administered to the patient
2. Include medication names with their dosages, routes, and durations when mentioned
3. Include specific procedures, surgeries, and other therapeutic interventions
4. Include supportive care measures that were implemented
5. DO NOT include planned or recommended treatments that were not confirmed to be administered
6. DO NOT include diagnostic procedures unless they also served a therapeutic purpose
7. DO NOT include general treatment discussions or literature reviews
8. BE EXTREMELY PRECISE - only include clearly stated treatments

Each treatment item should be in this format:
- [Treatment name/type]: [specific details like dosage, route, duration, technique] (if provided)

FORMAT YOUR RESPONSE AS A VALID JSON with the structure:
{
  "treatment_items": [
    "Item 1: with details when available",
    "Item 2: with details when available",
    ...
  ]
}

If no confirmed treatment items are found, return: {"treatment_items": []}
"""

# 直接从章节内容判断章节类型的模板
SECTION_TYPE_IDENTIFICATION_TEMPLATE = """
You are a medical literature analysis expert. You need to determine if the following section represents a specific type of medical content.

SECTION TYPE TO IDENTIFY: {section_type}

SECTION CONTENT:
{content}

Determine if this section is specifically a {section_type} section based on these criteria:

For "case_content" sections:
- Contains specific patient details (age, gender, medical history)
- Describes specific symptoms, signs, or clinical presentation
- Includes specific examination findings
- Provides a chronological narrative of a specific patient case
- Contains concrete, patient-specific information rather than general discussions

For "discussion" sections:
- Interprets or analyzes case findings
- Places the case in context of medical literature
- Discusses differential diagnoses, mechanisms, or theories
- References other studies or cases
- Contains more general statements rather than patient-specific details

For "treatment" sections:
- Details specific interventions performed
- Describes medications, surgical procedures, or other therapies
- Specifies dosages, durations, or techniques
- Outlines the clinical response to treatments
- Focuses specifically on management approaches rather than diagnosis or analysis

Respond ONLY with "YES" if the section clearly matches the specified type, or "NO" if it does not. 
Do not provide any explanation or additional text.
""" 