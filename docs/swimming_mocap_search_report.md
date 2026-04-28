# דו"ח חיפוש: מאגרי Motion Capture / Pose לשחייה עבור תרגום ל־Swumsuit באמצעות IK

תאריך: 2026-04-28

## מטרה

לאתר מאגרי נתונים רלוונטיים לשחייה שאפשר להשתמש בהם כדי להדגים תהליך המרה לפורמט `Swumsuit`, ובפרט יצירה או התאמה של `joint_motion.dat` באמצעות Inverse Kinematics.

## מסקנה כללית

מאגרי שחייה פתוחים שהם `motion capture` קלאסי בסגנון `C3D` או `Vicon` הם נדירים יחסית. לעומת זאת, קיימים כמה מאגרים שימושיים בפורמטים כמו `SMPL`, `3D joints`, `stereo + IMU`, ו־`2D keypoints`, שיכולים לשמש בסיס טוב להמרה ל־Swumsuit.

## המאגרים שנמצאו

### 1. SwimXYZ

סטטוס: ההמלצה הטובה ביותר להתחלה.

תיאור:
`SwimXYZ` הוא מאגר סינתטי ייעודי לשחייה. הוא כולל `3.4M` פריימים עם `2D/3D joints`, ובנוסף `240` רצפי תנועה בפורמט `SMPL`.

למה הוא מתאים:
- יש בו תנועות שחייה מפורשות, ולא רק פעילות אנושית כללית.
- אפשר לעבוד רק עם קובץ ה־motions בלי להוריד את כל הווידאו.
- `SMPL` מתאים יחסית בקלות לתהליך retargeting או IK אל שלד פשוט יותר כמו של Swumsuit.

חסרונות:
- המאגר סינתטי ולא נמדד ישירות משחיינים אמיתיים.
- יש צורך במיפוי בין שלד `SMPL` לבין הקונבנציות של Swumsuit.

קבצים רלוונטיים:
- `smpl_swimming_motions.zip` בגודל כ־`57.9 MB`

קישורים:
- דף הפרויקט: https://g-fiche.github.io/research-pages/swimxyz/
- הורדה של motions + annotations: https://zenodo.org/records/8399376

### 2. CADDY / DiverNet

סטטוס: מתאים כהדגמה של pose / orientation מהעולם האמיתי, פחות מתאים לדמו קלאסי של שחיית תחרות.

תיאור:
מאגר underwater אמיתי, הכולל `stereo footage` של צוללנים חופשיים במים יחד עם `IMU` מסונכרנים בחליפת `DiverNet`.

למה הוא מתאים:
- דאטה אמיתי.
- יכול לשמש להדגמה של IK מתוך `orientation` או `sensor fusion`.
- נותן ground truth מבוסס חיישנים ולא רק אנוטציה ידנית.

חסרונות:
- זה לא מאגר של שחיית freestyle/backstroke תחרותית.
- התנועה היא של צוללנים ולא של swimmers במבנה stroke קלאסי.
- כתובת ההורדה שצוינה במאמר עלולה להיות לא יציבה.

פרטים בולטים:
- כ־`12,708` זוגות תמונות rectified של free-swimming
- IMUs מסונכרנים משמשים כ־ground truth עבור pose / tracking

קישורים:
- מאמר: https://www.mdpi.com/2077-1312/7/1/16
- arXiv: https://arxiv.org/abs/1807.04856
- URL שמופיע במאמר: http://caddy-underwater-datasets.ge.issia.cnr.it/

### 3. Annotated Swimmer Pose Dataset

סטטוס: טוב מאוד לדמו של pipeline מווידאו ל־IK, אך לא mocap תלת־ממדי מלא.

תיאור:
מאגר של University of Augsburg עבור `backstroke`, עם `15 cycles` ויותר מ־`1200` פריימים מסומנים ידנית ב־`14 joints`.

למה הוא מתאים:
- תנועות שחייה אמיתיות.
- טוב לניסוי של `video -> 2D pose -> 3D lifting / IK -> Swumsuit`.
- קל יחסית לבנות עליו דמו מחקרי ברור.

חסרונות:
- `2D` בלבד, ללא `3D mocap`.
- מתאים בעיקר ל־backstroke ולא לכל סגנונות השחייה.

קישורים:
- דף המאגר: https://www.uni-augsburg.de/de/fakultaet/fai/informatik/prof/mmc/research/research_projects/swimmer_pose_estimation_dataset/
- דו"ח טכני: https://opus.bibliothek.uni-augsburg.de/opus4/files/1348/TR_2009_18.pdf

### 4. SJSU D1 Swim Dataset

סטטוס: מאגר מבטיח לשחייה אמיתית, טוב לדמו מווידאו, אך לא מספק mocap קלאסי.

תיאור:
מאגר פתוח חדש יחסית של שחיינים אמיתיים, שנבנה לצורכי swimmer detection, pose estimation, ו־stroke classification.

למה הוא מתאים:
- דאטה אמיתי של שחיינים.
- מכסה כמה סגנונות שחייה.
- יכול לשמש בסיס טוב למערכת markerless שמפיקה pose וממנה עוברים ל־IK.

חסרונות:
- לא `motion capture` תלת־ממדי ישיר.
- דורש שלב נוסף של pose estimation או lifting לפני יצירת נתוני Swumsuit.

קישורים:
- דף הפרויקט: https://sjsu-swimmervision.github.io/
- בדף הפרויקט יש גם קישור ל־dataset ב־Kaggle

### 5. HumanML3D + AMASS

סטטוס: fallback טוב לדמו טכני, פחות מומלץ לשחייה אם המטרה היא נאמנות ביומכנית.

תיאור:
`HumanML3D` כולל motions עם תוויות טקסטואליות, כולל `swimming`, ונבנה על גבי `AMASS`.

למה הוא מתאים:
- קל יחסית למצוא בו motion data מוכן בפורמט אחיד.
- `AMASS` הוא מאגר תנועה גדול ורחב מאוד.
- טוב לדמו של retargeting / IK כשלא חייבים שחייה תחרותית מדויקת.

חסרונות:
- לא מתמקד בשחייה.
- ב־`HumanML3D` הדאטה עצמו לא מחולק ישירות, אלא משוחזר מ־`AMASS`.
- דורש רישום, מודלים של `SMPL`, ועיבוד מקדים.

קישורים:
- HumanML3D: https://github.com/EricGuo5513/HumanML3D
- AMASS: https://amass.is.tue.mpg.de/

## דירוג פרקטי עבור הדגמת IK ל־Swumsuit

1. `SwimXYZ`
2. `Annotated Swimmer Pose Dataset`
3. `SJSU D1 Swim Dataset`
4. `CADDY / DiverNet`
5. `HumanML3D + AMASS`

## המלצה אופרטיבית

לצורך דמו ראשון:

1. להתחיל עם `SwimXYZ`, ובפרט עם `smpl_swimming_motions.zip`.
2. למפות את שלד `SMPL` לשלד הפשוט של Swumsuit.
3. להפיק זוויות מפרקים על ידי IK.
4. לכתוב `joint_motion.dat`.
5. לבדוק שהתנועה המתקבלת ב־Swumsuit דומה לתנועת המקור.

בשלב שני:

1. לעבור לדאטה אמיתי מבוסס וידאו, כמו Augsburg או SJSU.
2. להוסיף שלב markerless pose estimation לפני ה־IK.

## הערות על בחירת מאגר

- אם המטרה היא דמו מהיר ויציב: `SwimXYZ`.
- אם המטרה היא ריאליזם של swimmers אמיתיים: `Augsburg` או `SJSU`.
- אם המטרה היא להדגים שימוש ב־sensor-based orientation: `CADDY`.
- אם המטרה היא רק להוכיח pipeline של IK בלי תלות בשחייה תחרותית: `HumanML3D + AMASS`.

## מקורות

- SwimXYZ project page: https://g-fiche.github.io/research-pages/swimxyz/
- SwimXYZ Zenodo record: https://zenodo.org/records/8399376
- CADDY dataset paper: https://www.mdpi.com/2077-1312/7/1/16
- CADDY arXiv page: https://arxiv.org/abs/1807.04856
- University of Augsburg swimmer dataset page: https://www.uni-augsburg.de/de/fakultaet/fai/informatik/prof/mmc/research/research_projects/swimmer_pose_estimation_dataset/
- Augsburg technical report PDF: https://opus.bibliothek.uni-augsburg.de/opus4/files/1348/TR_2009_18.pdf
- SJSU swimmer project page: https://sjsu-swimmervision.github.io/
- HumanML3D repository: https://github.com/EricGuo5513/HumanML3D
- AMASS official site: https://amass.is.tue.mpg.de/
