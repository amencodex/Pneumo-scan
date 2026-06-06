(function () {
  const languageKey = "pneumoscan_language";
  const originalTitle = document.title;
  const originalText = new WeakMap();
  const originalAttributes = new WeakMap();
  let isApplying = false;
  let observer = null;

  const exact = new Map(Object.entries({
    "English": "እንግሊዝኛ",
    "Amharic": "አማርኛ",
    "Translate to Amharic": "ወደ አማርኛ ተርጉም",
    "Show English": "እንግሊዝኛ አሳይ",
    "PneumoScan Research": "የPneumoScan ምርምር",
    "PneumoScan Local": "PneumoScan አካባቢያዊ",
    "PneumoScan Research - Local Chest X-ray Model": "የPneumoScan ምርምር - አካባቢያዊ የደረት X-ray ሞዴል",
    "Local chest X-ray model": "የአካባቢ የደረት X-ray ሞዴል",
    "Dashboard": "ዳሽቦርድ",
    "Pneumonia": "የሳንባ ምች",
    "Care map": "የእንክብካቤ ካርታ",
    "Causes": "ምክንያቶች",
    "Prevention": "መከላከያ",
    "Sign in": "ግባ",
    "Sign in to dashboard": "ወደ ዳሽቦርድ ግባ",
    "Open care map": "የእንክብካቤ ካርታን ክፈት",
    "Private local research workspace": "የግል አካባቢያዊ የምርምር ቦታ",
    "Local scan preview": "የአካባቢ ስካን ቅድመ እይታ",
    "Model ready": "ሞዴሉ ዝግጁ ነው",
    "Image": "ምስል",
    "Signal": "ምልክት",
    "Review": "ግምገማ",
    "Admin": "አድሚን",
    "Research dashboard": "የምርምር ዳሽቦርድ",
    "Why pneumonia matters": "የሳንባ ምች ለምን አስፈላጊ ነው",
    "Pneumonia basics": "የሳንባ ምች መሠረታዊ መረጃ",
    "What is pneumonia?": "የሳንባ ምች ምንድን ነው?",
    "Simple explanation": "ቀላል ማብራሪያ",
    "Common signs:": "የተለመዱ ምልክቶች:",
    "Higher risk:": "ከፍተኛ አደጋ:",
    "Medical review matters:": "የሕክምና ግምገማ አስፈላጊ ነው:",
    "Safety first": "መጀመሪያ ደህንነት",
    "When should someone seek urgent care?": "ሰው መቼ አስቸኳይ እንክብካቤ መፈለግ አለበት?",
    "Urgent symptoms:": "አስቸኳይ ምልክቶች:",
    "Watch closely:": "በቅርብ ይከታተሉ:",
    "For this project:": "ለዚህ ፕሮጀክት:",
    "Care access": "የእንክብካቤ መዳረሻ",
    "Find help fast, then learn the scan flow.": "በፍጥነት እርዳታ ያግኙ፣ ከዚያ የስካን ሂደቱን ይማሩ።",
    "Nearest hospital finder": "ቅርብ ሆስፒታል መፈለጊያ",
    "Nearby hospitals": "ቅርብ ሆስፒታሎች",
    "Ready to open Maps when you need care directions.": "የእንክብካቤ አቅጣጫ ሲፈልጉ ካርታዎችን ለመክፈት ዝግጁ ነው።",
    "Offline pneumonia explainer": "የሳንባ ምች ከመስመር ውጭ ማብራሪያ",
    "Pneumonia explainer": "የሳንባ ምች ማብራሪያ",
    "Chest X-ray review flow": "የደረት X-ray ግምገማ ሂደት",
    "Learn what a chest X-ray involves": "የደረት X-ray ምን እንደሚያካትት ይማሩ",
    "What can cause pneumonia?": "የሳንባ ምችን ምን ሊያመጣ ይችላል?",
    "Bacteria": "ባክቴሪያ",
    "Viruses": "ቫይረሶች",
    "Fungi and risk factors": "ፈንገስና የአደጋ ምክንያቶች",
    "How to reduce risk": "አደጋን እንዴት መቀነስ ይቻላል",
    "Vaccines": "ክትባቶች",
    "Hand hygiene": "የእጅ ንፅህና",
    "Cleaner air": "ንጹህ አየር",
    "Sources": "ምንጮች",
    "Log in": "ግባ",
    "Sign up": "ተመዝገብ",
    "Username": "የተጠቃሚ ስም",
    "Password": "የይለፍ ቃል",
    "Log in and open dashboard": "ግባና ዳሽቦርዱን ክፈት",
    "Create account and open dashboard": "መለያ ፍጠርና ዳሽቦርዱን ክፈት",
    "Home": "መነሻ",
    "Check-ins": "ቼክ-ኢኖች",
    "Mail": "መልዕክት",
    "Learn": "ተማር",
    "Admin Hub": "የአድሚን ማዕከል",
    "Chats": "ቻቶች",
    "Booking Appointments": "ቀጠሮዎችን መያዝ",
    "Scan System": "የስካን ስርዓት",
    "Dark mode": "ጨለማ ሁነታ",
    "Light mode": "ብርሃን ሁነታ",
    "Log out": "ውጣ",
    "Toggle theme": "ገጽታ ቀይር",
    "Welcome back. Your mail and check-ins are ready.": "እንኳን ደህና ተመለሱ። መልዕክቶችዎና ቼክ-ኢኖችዎ ዝግጁ ናቸው።",
    "Admin-reviewed scans": "በአድሚን የተገመገሙ ስካኖች",
    "Open mail": "መልዕክት ክፈት",
    "Add check-in": "ቼክ-ኢን ጨምር",
    "Learn safety": "ደህንነትን ተማር",
    "Appointments": "ቀጠሮዎች",
    "Mail items": "የመልዕክት እቃዎች",
    "Admin-only scans": "ለአድሚን ብቻ የሆኑ ስካኖች",
    "Care file": "የእንክብካቤ ፋይል",
    "Temperature": "ሙቀት",
    "Oxygen level if measured": "ኦክስጅን መጠን ከተለካ",
    "Fluids note": "የፈሳሽ ማስታወሻ",
    "Food note": "የምግብ ማስታወሻ",
    "Notes": "ማስታወሻዎች",
    "Save check-in": "ቼክ-ኢን አስቀምጥ",
    "Mail from admin": "ከአድሚን የመጣ መልዕክት",
    "Refresh": "አድስ",
    "Chat with admin": "ከአድሚን ጋር ተወያይ",
    "Message": "መልዕክት",
    "Send message": "መልዕክት ላክ",
    "Patients": "ታካሚዎች",
    "Total scans": "ጠቅላላ ስካኖች",
    "High pattern": "ከፍተኛ ምልክት",
    "Messages": "መልዕክቶች",
    "Book appointment": "ቀጠሮ ያዝ",
    "Title": "ርዕስ",
    "Date / time": "ቀን / ሰዓት",
    "Send to user": "ለተጠቃሚው ላክ",
    "Analyze X-ray": "X-ray ተንትን",
    "Analyze blood support": "የደም ድጋፍን ተንትን",
    "Clear": "አጽዳ",
    "Clear blood sample": "የደም ናሙናውን አጽዳ",
    "Blood sample infection support": "የደም ናሙና የኢንፌክሽን ድጋፍ",
    "Next scan locked": "ቀጣይ ስካን ተቆልፏል",
    "No next scan": "ቀጣይ ስካን የለም",
    "X-ray signal": "የX-ray ምልክት",
    "Workflow:": "የስራ ሂደት:",
    "Next scan: Blood sample infection support": "ቀጣይ ስካን፦ የደም ናሙና የኢንፌክሽን ድጋፍ",
    "Working...": "በስራ ላይ...",
    "Sending...": "በመላክ ላይ...",
    "Sent.": "ተልኳል።",
    "Booking...": "ቀጠሮ በመያዝ ላይ...",
    "Appointment booked and sent to Mail.": "ቀጠሮው ተይዞ ወደ መልዕክት ተልኳል።",
    "Signed in locally": "በአካባቢው ገብተዋል",
    "Admin control room": "የአድሚን መቆጣጠሪያ ክፍል",
    "Loading patient record...": "የታካሚ መዝገብ በመጫን ላይ...",
    "No regular users have signed up yet.": "እስካሁን መደበኛ ተጠቃሚዎች አልተመዘገቡም።",
    "No appointments booked yet. New bookings from the admin will appear here.": "እስካሁን ቀጠሮ አልተያዘም። ከአድሚን የሚመጡ አዳዲስ ቀጠሮዎች እዚህ ይታያሉ።",
    "No extra notes.": "ተጨማሪ ማስታወሻ የለም።",
    "No scan": "ስካን የለም",
    "Status:": "ሁኔታ:",
    "User": "ተጠቃሚ",
    "Private care coordination portal": "የግል የእንክብካቤ ማስተባበሪያ ፖርታል",
    "Local backend": "አካባቢያዊ ባክኤንድ",
    "Sign in for private care updates.": "ለግል የእንክብካቤ ዝመናዎች ይግቡ።",
    "Your messages, appointments, and check-ins stay on this computer.": "መልዕክቶችዎ፣ ቀጠሮዎችዎና ቼክ-ኢኖችዎ በዚህ ኮምፒውተር ላይ ይቆያሉ።",
    "Chest X-ray scanning stays on the admin/doctor side.": "የደረት X-ray ስካን በአድሚን/ዶክተር በኩል ብቻ ይቆያል።",
    "This app is not a medical device. Pneumonia concerns should be reviewed by qualified clinicians.": "ይህ መተግበሪያ የሕክምና መሣሪያ አይደለም። የሳንባ ምች ጉዳዮች በብቁ የሕክምና ባለሙያዎች መገምገም አለባቸው።",
    "Local account": "አካባቢያዊ መለያ",
    "Privacy": "ግላዊነት",
    "Local private portal": "አካባቢያዊ የግል ፖርታል",
    "Your care updates, appointments, and messages in one clean place.": "የእንክብካቤ ዝመናዎችዎ፣ ቀጠሮዎችዎና መልዕክቶችዎ በአንድ ንጹሕ ቦታ።",
    "Scan details stay private on the admin side. You see only the appointments, notes, and instructions the admin chooses to send through Mail.": "የስካን ዝርዝሮች በአድሚን በኩል የግል ሆነው ይቆያሉ። እርስዎ የሚያዩት አድሚኑ በመልዕክት ለመላክ የመረጣቸውን ቀጠሮዎች፣ ማስታወሻዎችና መመሪያዎች ብቻ ነው።",
    "Chest X-ray scanning is admin/doctor-only. This portal is for private updates and tracking, not self-diagnosis.": "የደረት X-ray ስካን ለአድሚን/ዶክተር ብቻ ነው። ይህ ፖርታል ለግል ዝመናዎችና ክትትል ነው፣ ራስን ለመመርመር አይደለም።",
    "Built for controlled communication between the admin dashboard and regular users.": "በአድሚን ዳሽቦርድና በመደበኛ ተጠቃሚዎች መካከል ለተቆጣጠረ ግንኙነት ተገንብቷል።",
    "X-ray analysis stays in the admin dashboard so users do not self-read model results.": "ተጠቃሚዎች የሞዴል ውጤቶችን ራሳቸው እንዳያነቡ የX-ray ትንተና በአድሚን ዳሽቦርድ ውስጥ ይቆያል።",
    "Appointments, notes, and doctor/admin messages appear in one simple inbox.": "ቀጠሮዎች፣ ማስታወሻዎችና የዶክተር/አድሚን መልዕክቶች በአንድ ቀላል መልዕክት ሳጥን ውስጥ ይታያሉ።",
    "Users can track symptoms and share useful context without seeing private scan labels.": "ተጠቃሚዎች የግል የስካን መለያዎችን ሳያዩ ምልክቶችን መከታተልና ጠቃሚ መረጃ ማጋራት ይችላሉ።",
    "Accounts, messages, scans, and check-ins stay on this computer through the local backend.": "መለያዎች፣ መልዕክቶች፣ ስካኖችና ቼክ-ኢኖች በአካባቢያዊ ባክኤንድ በዚህ ኮምፒውተር ላይ ይቆያሉ።",
    "Patient-facing screens stay simple while admin-only clinical tools remain separated.": "ለታካሚ የሚታዩ ገጾች ቀላል ይቆያሉ፣ ለአድሚን ብቻ የሆኑ የሕክምና መሣሪያዎች ግን ተለይተው ይቆያሉ።",
    "The patient side avoids scan results and probabilities.": "የታካሚው ገጽ የስካን ውጤቶችንና ዕድሎችን አያሳይም።",
    "Clinical notes are sent only through Mail or appointments.": "የሕክምና ማስታወሻዎች በመልዕክት ወይም በቀጠሮ ብቻ ይላካሉ።",
    "Check-ins, messages, and bookings are easy to scan at a glance.": "ቼክ-ኢኖች፣ መልዕክቶችና ቦታ ማስያዣዎች በፍጥነት ለማየት ቀላል ናቸው።",
    "Appointments and messages from the admin account show up here.": "ከአድሚን መለያ የሚመጡ ቀጠሮዎችና መልዕክቶች እዚህ ይታያሉ።",
    "Ask a question or reply to the admin": "ጥያቄ ይጠይቁ ወይም ለአድሚኑ ይመልሱ",
    "Open a patient, then use the admin pages for chat, booking, and scan tools.": "ታካሚ ይክፈቱ፣ ከዚያ ለቻት፣ ለቀጠሮ መያዝና ለስካን መሣሪያዎች የአድሚን ገጾችን ይጠቀሙ።",
    "Open Admin Hub and choose a patient to start chatting.": "የአድሚን ማዕከልን ክፈቱና ለቻት ታካሚ ይምረጡ።",
    "Open Admin Hub and choose a patient to book appointments.": "የአድሚን ማዕከልን ክፈቱና ቀጠሮ ለመያዝ ታካሚ ይምረጡ።",
    "Open Admin Hub and choose a patient to run the scan system.": "የአድሚን ማዕከልን ክፈቱና የስካን ስርዓቱን ለማስኬድ ታካሚ ይምረጡ።",
    "AI model score for doctor review only. Not a diagnosis and not a patient self-scan.": "የAI ሞዴል ነጥብ ለዶክተር ግምገማ ብቻ ነው። ምርመራ አይደለም፣ የታካሚ ራስ-ስካንም አይደለም።",
    "Doctor checklist": "የዶክተር ማረጋገጫ ዝርዝር",
    "Evidence links": "የማስረጃ ሊንኮች",
    "Use this as clinician support only.": "ይህንን ለሕክምና ባለሙያ ድጋፍ ብቻ ይጠቀሙ።",
    "Bacterial support index": "የባክቴሪያ ድጋፍ መለኪያ",
    "Viral support index": "የቫይረስ ድጋፍ መለኪያ",
    "Other immune pattern": "ሌላ የኢሚዩን ምልክት",
    "Message this user": "ለዚህ ተጠቃሚ መልዕክት ይላኩ",
    "PneumoScan follow-up": "የPneumoScan ክትትል",
    "What the user should prepare or remember": "ተጠቃሚው ማዘጋጀት ወይም ማስታወስ ያለበት",
    "Example: Friday 3:00 PM": "ምሳሌ፦ ዓርብ 3:00 PM",
    "Example: 38.1 C or 100.6 F": "ምሳሌ፦ 38.1 C ወይም 100.6 F",
    "Example: 96%": "ምሳሌ፦ 96%",
    "Example: drank water regularly": "ምሳሌ፦ ውሃ በመደበኛነት ጠጣ",
    "Example: soup, fruit, small meals": "ምሳሌ፦ ሾርባ፣ ፍራፍሬ፣ ትንሽ ምግቦች",
    "Symptoms, medicines prescribed by clinician, follow-up reminders": "ምልክቶች፣ በሕክምና ባለሙያ የተዘዙ መድሃኒቶች፣ የክትትል ማስታወሻዎች"
  }));

  const replacements = [
    [/PneumoScan/g, "PneumoScan"],
    [/private care coordination portal/gi, "የግል የእንክብካቤ ማስተባበሪያ ፖርታል"],
    [/local private portal/gi, "አካባቢያዊ የግል ፖርታል"],
    [/chest X-ray/gi, "የደረት X-ray"],
    [/X-ray analysis/gi, "የX-ray ትንተና"],
    [/care updates/gi, "የእንክብካቤ ዝመናዎች"],
    [/scan details/gi, "የስካን ዝርዝሮች"],
    [/clinical notes/gi, "የሕክምና ማስታወሻዎች"],
    [/clinical tools/gi, "የሕክምና መሣሪያዎች"],
    [/medical device/gi, "የሕክምና መሣሪያ"],
    [/qualified clinicians/gi, "ብቁ የሕክምና ባለሙያዎች"],
    [/pneumonia-like pattern/gi, "የሳንባ ምች የሚመስል ምልክት"],
    [/pneumonia/gi, "የሳንባ ምች"],
    [/doctor\/admin/gi, "ዶክተር/አድሚን"],
    [/admin\/doctor/gi, "አድሚን/ዶክተር"],
    [/doctor/gi, "ዶክተር"],
    [/admin/gi, "አድሚን"],
    [/dashboard/gi, "ዳሽቦርድ"],
    [/appointments/gi, "ቀጠሮዎች"],
    [/appointment/gi, "ቀጠሮ"],
    [/messages/gi, "መልዕክቶች"],
    [/message/gi, "መልዕክት"],
    [/mail/gi, "መልዕክት"],
    [/patients/gi, "ታካሚዎች"],
    [/patient/gi, "ታካሚ"],
    [/scans/gi, "ስካኖች"],
    [/scan/gi, "ስካን"],
    [/X-ray/gi, "X-ray"],
    [/blood-cell/gi, "የደም-ሕዋስ"],
    [/blood/gi, "ደም"],
    [/support/gi, "ድጋፍ"],
    [/analysis/gi, "ትንተና"],
    [/analyze/gi, "ተንትን"],
    [/professional/gi, "ሙያዊ"],
    [/controlled/gi, "የተቆጣጠረ"],
    [/communication/gi, "ግንኙነት"],
    [/coordination/gi, "ማስተባበር"],
    [/portal/gi, "ፖርታል"],
    [/updates/gi, "ዝመናዎች"],
    [/instructions/gi, "መመሪያዎች"],
    [/computer/gi, "ኮምፒውተር"],
    [/clinicians/gi, "የሕክምና ባለሙያዎች"],
    [/clinician/gi, "የሕክምና ባለሙያ"],
    [/diagnosis/gi, "ምርመራ"],
    [/diagnose/gi, "መመርመር"],
    [/review/gi, "ግምገማ"],
    [/model/gi, "ሞዴል"],
    [/local/gi, "አካባቢያዊ"],
    [/private/gi, "የግል"],
    [/account/gi, "መለያ"],
    [/username/gi, "የተጠቃሚ ስም"],
    [/password/gi, "የይለፍ ቃል"],
    [/sign in/gi, "ግባ"],
    [/log in/gi, "ግባ"],
    [/sign up/gi, "ተመዝገብ"],
    [/log out/gi, "ውጣ"],
    [/refresh/gi, "አድስ"],
    [/clear/gi, "አጽዳ"],
    [/save/gi, "አስቀምጥ"],
    [/send/gi, "ላክ"],
    [/open/gi, "ክፈት"],
    [/book/gi, "ቀጠሮ ያዝ"],
    [/loading/gi, "በመጫን ላይ"],
    [/working/gi, "በስራ ላይ"],
    [/sending/gi, "በመላክ ላይ"],
    [/saved/gi, "ተቀምጧል"],
    [/ready/gi, "ዝግጁ"],
    [/locked/gi, "ተቆልፏል"],
    [/hidden/gi, "ተደብቋል"],
    [/details/gi, "ዝርዝሮች"],
    [/history/gi, "ታሪክ"],
    [/probabilities/gi, "ዕድሎች"],
    [/probability/gi, "ዕድል"],
    [/results/gi, "ውጤቶች"],
    [/result/gi, "ውጤት"],
    [/labels/gi, "መለያዎች"],
    [/label/gi, "መለያ"],
    [/condition/gi, "ሁኔታ"],
    [/status/gi, "ሁኔታ"],
    [/notes/gi, "ማስታወሻዎች"],
    [/care/gi, "እንክብካቤ"],
    [/safety/gi, "ደህንነት"],
    [/symptoms/gi, "ምልክቶች"],
    [/breathing/gi, "መተንፈስ"],
    [/cough/gi, "ሳል"],
    [/oxygen/gi, "ኦክስጅን"],
    [/temperature/gi, "ሙቀት"],
    [/fluids/gi, "ፈሳሾች"],
    [/food/gi, "ምግብ"],
    [/clean/gi, "ንጹሕ"],
    [/simple/gi, "ቀላል"],
    [/focused/gi, "ተወስኖ የተዘጋጀ"],
    [/separate/gi, "ተለየ"],
    [/separated/gi, "ተለይቷል"],
    [/regular/gi, "መደበኛ"],
    [/selected/gi, "የተመረጠ"],
    [/choose/gi, "ምረጥ"],
    [/upload/gi, "ስቀል"],
    [/preview/gi, "ቅድመ እይታ"],
    [/guidance/gi, "መመሪያ"],
    [/evidence/gi, "ማስረጃ"],
    [/links/gi, "ሊንኮች"],
    [/link/gi, "ሊንክ"],
    [/learn/gi, "ተማር"],
    [/home/gi, "መነሻ"],
    [/chat/gi, "ቻት"],
    [/users/gi, "ተጠቃሚዎች"],
    [/user/gi, "ተጠቃሚ"]
  ];

  const wordMap = new Map(Object.entries({
    a: "",
    an: "",
    the: "",
    and: "እና",
    or: "ወይም",
    to: "ወደ",
    from: "ከ",
    for: "ለ",
    with: "ከ",
    without: "ያለ",
    in: "ውስጥ",
    on: "ላይ",
    of: "የ",
    by: "በ",
    this: "ይህ",
    that: "ያ",
    these: "እነዚህ",
    those: "እነዚያ",
    your: "የእርስዎ",
    you: "እርስዎ",
    it: "እሱ",
    is: "ነው",
    are: "ናቸው",
    be: "ሁን",
    stay: "ይቆያል",
    stays: "ይቆያል",
    kept: "ተጠብቋል",
    only: "ብቻ",
    not: "አይደለም",
    no: "የለም",
    yes: "አዎ",
    new: "አዲስ",
    latest: "የቅርብ ጊዜ",
    recent: "የቅርብ ጊዜ",
    total: "ጠቅላላ",
    high: "ከፍተኛ",
    low: "ዝቅተኛ",
    medium: "መካከለኛ",
    normal: "መደበኛ",
    abnormal: "ያልተለመደ",
    severe: "ከባድ",
    mild: "ቀላል",
    private: "የግል",
    public: "ሕዝባዊ",
    local: "አካባቢያዊ",
    clean: "ንጹሕ",
    simple: "ቀላል",
    focused: "ተወስኖ የተዘጋጀ",
    controlled: "የተቆጣጠረ",
    ready: "ዝግጁ",
    hidden: "ተደብቋል",
    locked: "ተቆልፏል",
    available: "ይገኛል",
    unavailable: "አይገኝም",
    waiting: "በመጠበቅ ላይ",
    working: "በስራ ላይ",
    loading: "በመጫን ላይ",
    sending: "በመላክ ላይ",
    saved: "ተቀምጧል",
    sent: "ተልኳል",
    booked: "ተይዟል",
    created: "ተፈጥሯል",
    selected: "የተመረጠ",
    choose: "ምረጥ",
    chosen: "የተመረጠ",
    open: "ክፈት",
    close: "ዝጋ",
    clear: "አጽዳ",
    save: "አስቀምጥ",
    send: "ላክ",
    refresh: "አድስ",
    create: "ፍጠር",
    book: "ቀጠሮ ያዝ",
    upload: "ስቀል",
    run: "አስኪድ",
    use: "ተጠቀም",
    show: "አሳይ",
    hide: "ደብቅ",
    ask: "ጠይቅ",
    reply: "መልስ",
    track: "ተከታተል",
    share: "አጋራ",
    prepare: "አዘጋጅ",
    remember: "አስታውስ",
    review: "ግምገማ",
    reviewed: "የተገመገመ",
    analysis: "ትንተና",
    analyze: "ተንትን",
    diagnosis: "ምርመራ",
    diagnose: "መመርመር",
    model: "ሞዴል",
    models: "ሞዴሎች",
    score: "ነጥብ",
    signal: "ምልክት",
    pattern: "ምልክት",
    probability: "ዕድል",
    probabilities: "ዕድሎች",
    confidence: "እርግጠኝነት",
    result: "ውጤት",
    results: "ውጤቶች",
    label: "መለያ",
    labels: "መለያዎች",
    condition: "ሁኔታ",
    status: "ሁኔታ",
    detail: "ዝርዝር",
    details: "ዝርዝሮች",
    history: "ታሪክ",
    file: "ፋይል",
    files: "ፋይሎች",
    image: "ምስል",
    images: "ምስሎች",
    preview: "ቅድመ እይታ",
    view: "እይታ",
    page: "ገጽ",
    pages: "ገጾች",
    dashboard: "ዳሽቦርድ",
    home: "መነሻ",
    portal: "ፖርታል",
    account: "መለያ",
    username: "የተጠቃሚ ስም",
    password: "የይለፍ ቃል",
    user: "ተጠቃሚ",
    users: "ተጠቃሚዎች",
    admin: "አድሚን",
    doctor: "ዶክተር",
    clinician: "የሕክምና ባለሙያ",
    clinicians: "የሕክምና ባለሙያዎች",
    patient: "ታካሚ",
    patients: "ታካሚዎች",
    care: "እንክብካቤ",
    medical: "የሕክምና",
    clinical: "የሕክምና",
    safety: "ደህንነት",
    privacy: "ግላዊነት",
    communication: "ግንኙነት",
    coordination: "ማስተባበር",
    update: "ዝመና",
    updates: "ዝመናዎች",
    instruction: "መመሪያ",
    instructions: "መመሪያዎች",
    note: "ማስታወሻ",
    notes: "ማስታወሻዎች",
    message: "መልዕክት",
    messages: "መልዕክቶች",
    mail: "መልዕክት",
    chat: "ቻት",
    chats: "ቻቶች",
    appointment: "ቀጠሮ",
    appointments: "ቀጠሮዎች",
    booking: "ቀጠሮ መያዝ",
    bookings: "ቦታ ማስያዣዎች",
    check: "ማረጋገጫ",
    checkin: "ቼክ-ኢን",
    checkins: "ቼክ-ኢኖች",
    scan: "ስካን",
    scans: "ስካኖች",
    system: "ስርዓት",
    tool: "መሣሪያ",
    tools: "መሣሪያዎች",
    workflow: "የስራ ሂደት",
    flow: "ሂደት",
    support: "ድጋፍ",
    guidance: "መመሪያ",
    advice: "ምክር",
    action: "እርምጃ",
    actions: "እርምጃዎች",
    checklist: "ማረጋገጫ ዝርዝር",
    evidence: "ማስረጃ",
    link: "ሊንክ",
    links: "ሊንኮች",
    source: "ምንጭ",
    sources: "ምንጮች",
    research: "ምርምር",
    study: "ጥናት",
    studies: "ጥናቶች",
    pneumonia: "የሳንባ ምች",
    lung: "ሳንባ",
    lungs: "ሳንባዎች",
    chest: "ደረት",
    breathing: "መተንፈስ",
    breath: "ትንፋሽ",
    cough: "ሳል",
    oxygen: "ኦክስጅን",
    temperature: "ሙቀት",
    fever: "ትኩሳት",
    symptom: "ምልክት",
    symptoms: "ምልክቶች",
    fluid: "ፈሳሽ",
    fluids: "ፈሳሾች",
    food: "ምግብ",
    blood: "ደም",
    bacterial: "የባክቴሪያ",
    bacteria: "ባክቴሪያ",
    viral: "የቫይረስ",
    virus: "ቫይረስ",
    viruses: "ቫይረሶች",
    immune: "የኢሚዩን",
    cell: "ሕዋስ",
    cells: "ሕዋሶች",
    type: "አይነት",
    index: "መለኪያ",
    other: "ሌላ",
    neutrophil: "ኒውትሮፊል",
    lymphocyte: "ሊምፎሳይት",
    monocyte: "ሞኖሳይት",
    eosinophil: "ኢዮሲኖፊል",
    basophil: "ቤሶፊል",
    sample: "ናሙና",
    xray: "X-ray",
    x: "X",
    ray: "ray",
    log: "ግባ",
    login: "መግቢያ",
    signup: "መመዝገቢያ",
    logout: "መውጫ",
    sign: "ግባ",
    in: "ውስጥ",
    out: "ውጣ",
    dark: "ጨለማ",
    light: "ብርሃን",
    mode: "ሁነታ",
    theme: "ገጽታ",
    toggle: "ቀይር",
    date: "ቀን",
    time: "ሰዓት",
    friday: "ዓርብ",
    today: "ዛሬ",
    tomorrow: "ነገ",
    first: "መጀመሪያ",
    second: "ሁለተኛ",
    next: "ቀጣይ",
    previous: "ቀዳሚ",
    current: "የአሁኑ",
    average: "አማካይ",
    count: "ብዛት",
    items: "እቃዎች",
    item: "እቃ",
    list: "ዝርዝር",
    record: "መዝገብ",
    records: "መዝገቦች",
    room: "ክፍል",
    hub: "ማዕከል",
    built: "ተገንብቷል",
    between: "መካከል",
    regular: "መደበኛ",
    facing: "የሚታይ",
    screens: "ገጾች",
    remain: "ይቆያል",
    remains: "ይቆያል",
    separated: "ተለይቷል",
    side: "በኩል",
    through: "በኩል",
    appear: "ይታያል",
    appears: "ይታያል",
    here: "እዚህ",
    concerns: "ጉዳዮች",
    should: "መሆን አለበት",
    qualified: "ብቁ",
    device: "መሣሪያ",
    score: "ነጥብ",
    self: "ራስ",
    read: "አንብብ",
    send: "ላክ",
    sent: "ተልኳል",
    saved: "ተቀምጧል"
  }));

  function addControls() {
    if (document.getElementById("languageToggle")) return;
    const style = document.createElement("style");
    style.id = "languageToggleStyle";
    style.textContent = `
      body.amharic-mode {
        font-family: "Noto Sans Ethiopic", Nyala, "Abyssinica SIL", Inter, ui-sans-serif, system-ui, sans-serif;
      }
      .language-toggle {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 9998;
        min-height: 44px;
        border: 1px solid rgba(12, 170, 138, .24);
        border-radius: 999px;
        padding: 0 15px;
        color: white;
        background: linear-gradient(135deg, #0caa8a, #2f79d6);
        box-shadow: 0 18px 42px rgba(12, 170, 138, .28);
        font-weight: 950;
        cursor: pointer;
      }
      .language-toggle:hover {
        transform: translateY(-2px);
        box-shadow: 0 22px 52px rgba(12, 170, 138, .34);
      }
    `;
    document.head.appendChild(style);

    const button = document.createElement("button");
    button.id = "languageToggle";
    button.className = "language-toggle";
    button.type = "button";
    button.setAttribute("data-i18n-ignore", "true");
    button.addEventListener("click", () => {
      const nextLanguage = currentLanguage() === "am" ? "en" : "am";
      localStorage.setItem(languageKey, nextLanguage);
      if (nextLanguage === "en") {
        window.location.reload();
        return;
      }
      setLanguage("am");
    });
    document.body.appendChild(button);
  }

  function currentLanguage() {
    return localStorage.getItem(languageKey) === "am" ? "am" : "en";
  }

  function translateText(value) {
    if (!value || !value.trim()) return value;
    const leading = value.match(/^\s*/)[0];
    const trailing = value.match(/\s*$/)[0];
    const trimmed = value.trim();
    let translated = exact.get(trimmed);
    if (!translated) {
      translated = trimmed;
      replacements.forEach(([pattern, replacement]) => {
        translated = translated.replace(pattern, replacement);
      });
    }
    translated = translated.replace(/\b[A-Za-z][A-Za-z-]*\b/g, (word) => {
      if (/^(PneumoScan|AI|X|ray|X-ray|RSV|Hib|MP4|GLB|WebGL|URL|JSON|API)$/i.test(word)) return word;
      return wordMap.get(word.toLowerCase()) || word;
    });
    return leading + translated + trailing;
  }

  function looksLikeFreshEnglish(value) {
    return /[A-Za-z]/.test(value || "") && !/[\u1200-\u137F]/.test(value || "");
  }

  function shouldSkip(node) {
    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (!element) return true;
    return Boolean(element.closest(
      "script, style, noscript, code, pre, [data-i18n-ignore], " +
      ".source-list a, .evidence-links a, " +
      "a[href*='who.int'], a[href*='cdc.gov'], a[href*='nih.gov'], " +
      "a[href*='rsna.org'], a[href*='kaggle.com'], a[href*='radiologyinfo.org']"
    ));
  }

  function translateNodeText(node, language) {
    if (shouldSkip(node)) return;
    if (!originalText.has(node) || (language === "am" && looksLikeFreshEnglish(node.nodeValue))) {
      originalText.set(node, node.nodeValue);
    }
    node.nodeValue = language === "am" ? translateText(originalText.get(node)) : originalText.get(node);
  }

  function translateAttributes(element, language) {
    if (shouldSkip(element)) return;
    const attrs = ["placeholder", "title", "aria-label", "alt"];
    attrs.forEach((name) => {
      if (!element.hasAttribute(name)) return;
      let store = originalAttributes.get(element);
      if (!store) {
        store = {};
        originalAttributes.set(element, store);
      }
      const current = element.getAttribute(name);
      if (!(name in store) || (language === "am" && looksLikeFreshEnglish(current))) store[name] = current;
      element.setAttribute(name, language === "am" ? translateText(store[name]) : store[name]);
    });

    if (element.matches("input[value]") && element.type !== "password" && element.type !== "file") {
      let store = originalAttributes.get(element);
      if (!store) {
        store = {};
        originalAttributes.set(element, store);
      }
      const currentValue = element.getAttribute("value");
      if (!("value" in store) || (language === "am" && looksLikeFreshEnglish(currentValue))) store.value = currentValue;
      const translatedValue = language === "am" ? translateText(store.value) : store.value;
      element.setAttribute("value", translatedValue);
      if (!element.matches(":focus")) element.value = translatedValue;
    }
  }

  function walk(root, language) {
    if (!root || shouldSkip(root)) return;
    if (root.nodeType === Node.TEXT_NODE) {
      translateNodeText(root, language);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return;
    if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root, language);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let node = walker.currentNode;
    while (node) {
      if (node.nodeType === Node.TEXT_NODE) translateNodeText(node, language);
      if (node.nodeType === Node.ELEMENT_NODE) translateAttributes(node, language);
      node = walker.nextNode();
    }
  }

  function updateButton(language) {
    const button = document.getElementById("languageToggle");
    if (!button) return;
    button.textContent = language === "am" ? "English" : "አማርኛ";
    button.setAttribute("aria-label", language === "am" ? "Show English" : "Translate to Amharic");
  }

  function setLanguage(language) {
    addControls();
    isApplying = true;
    localStorage.setItem(languageKey, language);
    document.documentElement.lang = language === "am" ? "am" : "en";
    document.title = language === "am" ? translateText(originalTitle) : originalTitle;
    document.body.classList.toggle("amharic-mode", language === "am");
    walk(document.body, language);
    updateButton(language);
    isApplying = false;
  }

  function observeChanges() {
    if (observer) return;
    observer = new MutationObserver((mutations) => {
      if (isApplying || currentLanguage() !== "am") return;
      window.clearTimeout(observeChanges.timer);
      observeChanges.timer = window.setTimeout(() => {
        isApplying = true;
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => walk(node, "am"));
          if (mutation.type === "characterData") translateNodeText(mutation.target, "am");
          if (mutation.type === "attributes") translateAttributes(mutation.target, "am");
        });
        updateButton("am");
        isApplying = false;
      }, 25);
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["placeholder", "title", "aria-label", "alt"]
    });
  }

  window.pneumoSetLanguage = setLanguage;
  window.pneumoApplyLanguage = () => setLanguage(currentLanguage());

  document.addEventListener("DOMContentLoaded", () => {
    addControls();
    setLanguage(currentLanguage());
    observeChanges();
  });
})();
