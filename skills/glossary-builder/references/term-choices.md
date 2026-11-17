# Term choices

Established renderings for terms that appear in Arabic technical, academic, and
product writing. This is a starting point, not a mandate: the project's own
glossary wins. Where usage genuinely splits, the note says so and you should pick
one per project and record it.

## Software and engineering

| English | Recommended | Acceptable alternative | Note |
| --- | --- | --- | --- |
| repository | مستودع | مخزن | مستودع in docs; ريبو only in chat |
| commit | إيداع | تثبيت، كوميت | Verb form: أودع/يودع; noun: إيداع |
| branch | فرع | | Never "شعبة" |
| merge | دمج | ضم | دمج is standard in Git tooling |
| pull request | طلب دمج | طلب سحب | طلب دمج matches the Git Arabic UI |
| issue | مسألة | مشكلة، تذكرة | تذكرة in issue-tracker context |
| build | بناء | تجميع | Keep `build` in code spans |
| deploy / deployment | نشر | توزيع | نشر for both noun and verb |
| environment | بيئة | محيط | بيئة always in software contexts |
| configuration | إعدادات | تهيئة | إعدادات for UI; تهيئة in prose |
| dependency | اعتمادية | تبعية | تبعية is more common in docs |
| package | حزمة | | |
| library | مكتبة | | |
| framework | إطار عمل | إطار | إطار عمل in prose, إطار in headings |
| runtime | بيئة التشغيل | زمن التشغيل | بيئة التشغيل is clearer for beginners |
| cache | ذاكرة مؤقتة | كاش | كاش acceptable in dev docs |
| token | رمز | توكن | رمز in docs, توكن in API contexts |
| endpoint | نقطة نهاية | نقطة وصول | نقطة نهاية matches the concept |
| payload | الحمولة | البيانات المُرسَلة | الحمولة in API docs |
| middleware | برمجيات وسيطة | وسيط | "طبقة وسيطة" reads better in prose |
| thread | خيط | مسار | خيط for OS threads; مسار for execution path |
| queue | طابور | صف | طابور in CS contexts |
| pipeline | خط أنابيب | مسار معالجة | مسار معالجة reads better outside cloud docs |
| schema | مخطط | هيكل | مخطط for data schemas |
| migration | ترحيل | هجرة | ترحيل for data; هجرة only for people |
| sandbox | بيئة معزولة | صندوق رمل | صندوق رمل is a calque; avoid in prose |
| container | حاوية | | |
| image (container) | صورة | | |
| instance | نسخة | مثيل | نسخة for services, مثيل for OOP objects |
| volume (storage) | وحدة تخزين | مجلد | وحدة تخزين for cloud storage |
| region | منطقة | إقليم | منطقة in cloud contexts |
| bucket | دلو | حاوية | دلو is the accepted cloud term |
| latency | زمن الوصول | التأخير | زمن الوصول is more precise |
| throughput | معدل النقل | الإنتاجية | معدل النقل for networks |
| fallback | بديل احتياطي | احتياطي | بديل احتياطي in prose |
| deprecation | إهمال | | "مهمَل" for the state |

## AI and data

| English | Recommended | Note |
| --- | --- | --- |
| model | نموذج | |
| training | تدريب | |
| inference | استدلال | "تشغيل النموذج" when استدلال confuses the reader |
| prompt | موجه | برومبت in practitioner chat; موجه in docs |
| token (LLM) | وحدة نصية | رمز conflicts with auth tokens; disambiguate |
| embedding | تضمين | |
| fine-tuning | ضبط دقيق | |
| benchmark | اختبار مرجعي | معيار in casual prose |
| dataset | مجموعة بيانات | |
| label | تصنيف / وسم | وسم for annotations |
| feature (ML) | سمة | Not ميزة — that means "product feature" |
| parameter | معامل | متغير for statistics |
| hyperparameter | معامل فائق | |
| epoch | دورة تدريبية | حقبة in older texts |
| overfitting | الإفراط في التخصيص | |
| agent | وكيل | In agentic AI; عامل for a generic process |
| tool call | استدعاء أداة | |
| context window | نافذة السياق | |

## Academic and general

| English | Recommended | Note |
| --- | --- | --- |
| abstract (paper) | الملخّص | |
| methodology | المنهجية | |
| hypothesis | فرضية | |
| significance | الدلالة | دلالة إحصائية for statistical |
| correlation | ارتباط | Never علاقة سببية |
| caveat | تحفّظ | |
| trade-off | مقايضة | موازنة between options |
| best practice | أفضل الممارسات | |
| guideline | إرشاد / دليل إرشادي | |
| requirement | متطلب | |
| specification | مواصفة | |
| deliverable | مُخرَج | |
| stakeholder | صاحب مصلحة | |
| roadmap | خارطة طريق | |
| onboarding | التهيئة الأولية | Never "التحاق" |
| changelog | سجل التغييرات | |

## Traps

| Word | Trap |
| --- | --- |
| feature | ميزة (product) vs سمة (ML) — two entries, not one |
| instance | نسخة (service) vs مثيل (object) |
| argument | وسيط (function) vs حجة (debate) |
| statement | عبارة (code) vs بيان (official) |
| value | قيمة (general) vs قيمة (ethics) |
| run | تشغيل (software) vs إدارة (business) |
| fetch | جلب not إحضار |
| support | يدعم (technical) vs يؤيد (opinion) — never conflate |
| control | تحكّم (systems) vs سيطرة (management) |
| current | حالي (time) vs تيار (electricity) |
| thread | خيط vs مسار |
| table | جدول (data) vs طاولة (furniture) |

Every one of these becomes two entries with distinct aliases, or one entry with a
note that disambiguates the domain.
