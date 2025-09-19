from gtts import gTTS

text = "Kamu sudah ambil makanan hari ini"
tts = gTTS(text=text, lang='id')
tts.save("static/sounds/sudah_diambil.mp3")

text = "Ref ID tidak terdaftar. Silakan hubungi HRD."
tts = gTTS(text=text, lang='id')
tts.save("static/sounds/hubungi_hrd.mp3")

text = "Silakan mengambil makanan hari ini!"
tts = gTTS(text=text, lang='id')
tts.save("static/sounds/sukses_ambil.mp3")