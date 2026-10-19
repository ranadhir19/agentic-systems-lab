# Intent inference vs intent classification — results

Seed 7; 20 frozen test cases; both systems graded identically.

## Aggregate metrics

| Metric | Classifier (TF-IDF + softmax) | Inference pipeline |
|---|---|---|
| mean_recall | 0.567 | 1.0 |
| mean_precision | 0.65 | 1.0 |
| task_success | 0.45 | 1.0 |
| paraphrase_consistency | 0.417 | 1.0 |
| context_accuracy | 0.333 | 1.0 |
| clarification turns (useless rephrase / targeted) | 7 / 0 | 0 / 6 |

## Success rate by phenomenon

| Phenomenon | n | Classifier | Pipeline |
|---|---|---|---|
| paraphrase | 5 | 0.4 | 1.0 |
| multi_intent | 3 | 0.0 | 1.0 |
| latent | 2 | 0.5 | 1.0 |
| dynamic | 1 | 0.0 | 1.0 |
| context | 3 | 0.333 | 1.0 |
| out_of_catalog | 2 | 0.0 | 1.0 |
| standard | 5 | 1.0 | 1.0 |

## Per-case detail (classifier)

| Case | Utterance | Produced | Expected | Success | Clarify |
|---|---|---|---|---|---|
| p1 | I want to know my balance | ['check_balance'] | ['check_balance'] | True | 0 |
| p2 | How much money do I have? | ['unknown'] | ['check_balance'] | False | 1 |
| p3 | Can you tell me whether I can afford lunch today? | ['unknown'] | ['check_balance'] | False | 1 |
| p4 | Transfer $200 to my savings account | ['transfer_money'] | ['transfer_money'] | True | 0 |
| p5 | Could you move two hundred bucks into savings for me | ['unknown'] | ['transfer_money'] | False | 1 |
| m1 | I forgot my password, but I also changed my phone nu | ['update_phone'] | ['auth_assistance', 'reset_password', 'update_phone'] | False | 0 |
| m2 | My laptop is overheating and I also forgot my Wi-Fi  | ['wifi_help'] | ['laptop_support', 'wifi_help'] | False | 0 |
| m3 | Cancel my booking and book a flight to Denver | ['cancel_booking'] | ['book_flight', 'cancel_booking'] | False | 0 |
| l1 | I'm hungry | ['unknown'] | ['food_need'] | False | 1 |
| l2 | I have an interview tomorrow | ['interview_prep'] | ['interview_prep'] | True | 0 |
| d1 | What should I wear? | ['interview_prep', 'unknown'] | ['attire_advice', 'interview_prep'] | False | 1 |
| c1 | Make it cheaper | ['book_hotel', 'unknown'] | ['book_hotel', 'refine_search'] | False | 1 |
| c2 | Actually cancel it | ['cancel_booking', 'track_order'] | ['cancel_booking', 'track_order'] | True | 0 |
| o1 | Can you write a haiku about my router? | ['unknown'] | ['creative_writing'] | False | 1 |
| o2 | My Apple laptop screen becomes dark after login | ['laptop_support'] | ['diagnose_display'] | False | 0 |
| s1 | Where is my order? | ['track_order'] | ['track_order'] | True | 0 |
| s2 | I forgot my wifi password | ['wifi_help'] | ['wifi_help'] | True | 0 |
| s3 | Recommend a good restaurant | ['restaurant_suggestion'] | ['restaurant_suggestion'] | True | 0 |
| s4 | Cancel my booking | ['cancel_booking'] | ['cancel_booking'] | True | 0 |
| s5 | Book a flight to Denver | ['book_flight'] | ['book_flight'] | True | 0 |

## Per-case detail (pipeline)

| Case | Produced | Expected | Success | Targeted Qs | Used ctx |
|---|---|---|---|---|---|
| p1 | ['check_balance'] | ['check_balance'] | True | 0 | False |
| p2 | ['check_balance'] | ['check_balance'] | True | 0 | False |
| p3 | ['check_balance'] | ['check_balance'] | True | 0 | False |
| p4 | ['transfer_money'] | ['transfer_money'] | True | 0 | False |
| p5 | ['transfer_money'] | ['transfer_money'] | True | 0 | False |
| m1 | ['auth_assistance', 'reset_password', 'update_phone'] | ['auth_assistance', 'reset_password', 'update_phone'] | True | 0 | False |
| m2 | ['laptop_support', 'wifi_help'] | ['laptop_support', 'wifi_help'] | True | 0 | False |
| m3 | ['book_flight', 'cancel_booking'] | ['book_flight', 'cancel_booking'] | True | 1 | False |
| l1 | ['food_need'] | ['food_need'] | True | 0 | False |
| l2 | ['interview_prep'] | ['interview_prep'] | True | 0 | False |
| d1 | ['attire_advice', 'interview_prep'] | ['attire_advice', 'interview_prep'] | True | 1 | True |
| c1 | ['book_hotel', 'refine_search'] | ['book_hotel', 'refine_search'] | True | 1 | True |
| c2 | ['cancel_booking', 'track_order'] | ['cancel_booking', 'track_order'] | True | 0 | True |
| o1 | ['creative_writing'] | ['creative_writing'] | True | 0 | False |
| o2 | ['diagnose_display'] | ['diagnose_display'] | True | 2 | False |
| s1 | ['track_order'] | ['track_order'] | True | 0 | False |
| s2 | ['wifi_help'] | ['wifi_help'] | True | 0 | False |
| s3 | ['restaurant_suggestion'] | ['restaurant_suggestion'] | True | 0 | False |
| s4 | ['cancel_booking'] | ['cancel_booking'] | True | 0 | False |
| s5 | ['book_flight'] | ['book_flight'] | True | 1 | False |

## o2 walkthrough: laptop display (structured goal)

Utterance: `My Apple laptop screen becomes dark after login`

- goal `diagnose_display` (confidence 0.95)
  - constraint: issue occurs only after login; OS-level, not hardware POST
  - constraint: device=laptop
  - missing info: Is an external monitor connected, and does it show anything?
  - missing info: Have you tried booting into safe mode?

Questions asked: ['Is an external monitor connected, and does it show anything?', 'Have you tried booting into safe mode?']
Expected missing-info covered: {'safe mode': True, 'external monitor': True}

Pipeline response: To help: Is an external monitor connected, and does it show anything? Have you tried booting into safe mode? [SupportAgent] diagnose_display: diagnosis started: display subsystem.

## Reading the numbers

- The classifier is perfect on canonical phrasings (5/5 standard cases) and collapses everywhere else: 0% on multi-intent (one label cannot hold three goals), 0% on out-of-catalog, 40% on paraphrases.
- Its 7 'clarifications' are all the same useless fallback ('Sorry, I didn't understand. Please rephrase.').
- The pipeline's 6 clarifications are targeted missing-info questions (diagnostic questions, dates, dress code) — asked only when the evidence check shows the info is absent.
- No utterance ever yields 'unknown': the worst case is a best-effort `general_assist` goal with a clarification question (graceful degradation).

