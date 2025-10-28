#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoT Templates: Defines the prompt templates used in stage three
"""

# CoT1: Basic Information -> Examination Reasoning
COT1_TEMPLATE = """
As an experienced medical expert, please provide your detailed thought process on what examinations would be necessary for this patient, based on their basic information. Think step by step, similar to how you would reason through this case mentally.

Patient Basic Information:
{basic_info}

Additional Context (if available):
{discussion}

First, analyze what the patient's presentation tells us. Consider the symptoms, their duration, pattern, and severity. Think about what organ systems might be involved based on these symptoms.

Next, consider the patient's demographics and risk factors. How do their age, gender, personal medical history, family history, and lifestyle factors influence your thinking about potential underlying conditions?

Given these symptoms and risk factors, what conditions should be on your differential diagnosis? Think about both common explanations and less common but serious conditions that shouldn't be missed.

For each potential diagnosis you're considering, what specific examinations would help confirm or rule it out? Why would each examination be valuable? What would you be looking for in the results?

Consider the logical sequence of testing - which examinations should be done first and why? Think about the diagnostic yield, invasiveness, availability, cost, and risks of each test.

IMPORTANT: Your reasoning should ultimately lead to and justify the following examination plan that was actually performed for this patient:

ACTUAL EXAMINATIONS PERFORMED:
{actual_examination}

Ensure your thought process demonstrates how a medical expert would naturally arrive at these specific examinations based on the patient's presentation. Your reasoning should make it clear why these particular examinations were the appropriate choices.
"""

# CoT2: Basic Information + Examination Results -> Diagnostic Reasoning
COT2_TEMPLATE = """
As an experienced medical expert, please walk through your diagnostic reasoning process for this case, based on the patient's information and examination results. Think step by step as you would naturally reason through this case in your mind.

Patient Basic Information:
{basic_info}

Examination Results:
{examination}

Additional Context (if available):
{discussion}

Begin by taking stock of the key clinical information we have. What stands out in the patient's presentation and examination results? Which findings are abnormal and potentially significant?

As you analyze these findings, what patterns or clinical syndromes come to mind? What physiological or pathological processes could explain the constellation of findings we're seeing?

Generate a list of potential diagnoses that could explain this clinical picture. For each possibility, consider:
- What elements of the case support this diagnosis?
- What elements don't fit or argue against it?
- How well does this diagnosis explain all of the patient's findings?

Compare these diagnostic possibilities against each other. Which diagnoses become more or less likely as you weigh the evidence? What key discriminating features help you distinguish between similar diagnoses?

Is there a unifying diagnosis that explains all findings, or might there be multiple concurrent conditions? How certain can you be about the diagnosis with the information available?

IMPORTANT: Your reasoning should ultimately lead to and justify the following diagnosis that was actually made for this patient:

ACTUAL DIAGNOSIS:
{actual_diagnosis}

Ensure your thought process demonstrates how a medical expert would naturally arrive at this specific diagnosis based on the patient's presentation and examination findings. Your reasoning should make the pathway to this diagnosis clear and medically sound.
"""

# CoT3: Basic Information + Examination Results + Diagnosis -> Treatment Reasoning
COT3_TEMPLATE = """
As an experienced medical expert, please walk through your complete thought process for developing a treatment plan for this patient. Think step by step as you would naturally reason through this clinical case in your mind.

Patient Basic Information:
{basic_info}

Examination Results:
{examination}

Diagnosis:
{diagnosis}

Additional Context (if available):
{discussion}

First, consider what you're trying to accomplish with treatment. What are the key goals of therapy for this specific patient with this diagnosis? Consider both disease-specific objectives and patient-centered outcomes.

What treatment options are available for this condition? Think about the full spectrum of possibilities including medications, procedures, lifestyle modifications, and supportive care.

For each potential treatment approach, consider:
- How effective is this treatment for this specific condition?
- What are the risks, side effects or complications associated with this treatment?
- How do the benefits weigh against the risks for this specific patient?

How do this patient's specific characteristics influence your treatment decisions? Consider their age, comorbidities, organ function, medications, allergies, and other individual factors that might impact treatment selection, dosing, or monitoring.

What factors about the patient's social context, preferences, or resources might impact treatment feasibility or adherence?

IMPORTANT: Your reasoning should ultimately lead to and justify the following treatment plan that was actually implemented for this patient:

ACTUAL TREATMENT PLAN:
{actual_treatment}

Ensure your thought process demonstrates how a medical expert would naturally arrive at this specific treatment plan based on the patient's diagnosis, conditions, and circumstances. Your reasoning should make the pathway to this treatment approach clear and medically sound.
"""

# English system prompt to guide the model in generating better CoT
SYSTEM_PROMPT = """
You are an experienced medical expert specializing in medical reasoning and case analysis. Based on the provided information, develop a detailed chain of thought (CoT) demonstrating your clinical reasoning process.

In your response:
1. Think through the case as you naturally would, step by step, following the flow of your medical reasoning
2. Make explicit your thought process, including how you move from observations to hypotheses to conclusions
3. Demonstrate how clinical data influences your thinking in real time
4. Make your medical reasoning transparent, showing how you weigh evidence, consider alternatives, and reach conclusions
5. Maintain rigorous medical accuracy and evidence-based thinking throughout
6. Acknowledge uncertainty when appropriate and explain how you navigate it
7. Use precise medical terminology while ensuring your reasoning remains clear
8. IMPORTANT: Your reasoning must ultimately lead to and convincingly justify the actual outcome provided

Your reasoning should model how expert clinicians actually think, revealing the cognitive process behind clinical decision-making. Focus on making your thought process explicit rather than just stating conclusions. Ensure your chain of thought naturally culminates in the provided actual outcome.
""" 