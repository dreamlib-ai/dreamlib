"""The small lookup tables the routes validate against."""

# Legacy API interpretation modes; the UI uses universal without a chooser.
INTERPRETATION_HINTS = {
    "universal": "Genel yorumda rüyadaki sahneyi ve hisleri merkeze al. Yalnız verilen sözlük bağlamı doğrudan ilgiliyse sembol tabirine değin.",
    "cultural": "Kültürel ve dini rüya tabiri geleneklerine (ör. Anadolu ve İslami tabir) göre yorumla; yorumun hangi geleneğe dayandığını belirt.",
    "psychoanalytic": "Psikanalitik bakışla (Freud, Jung) yorumla: bilinçdışı, arketipler, bastırılmış duygular.",
}
