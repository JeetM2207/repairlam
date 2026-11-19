with open("/home/23ucs603/btp/serve32.sh", "r") as f:
    text = f.read()
text = text.replace("[ \"$CTX\" -gt 32768 ] && CTX=32768", "[ \"$CTX\" -gt 16000 ] && CTX=16000")
with open("/home/23ucs603/btp/serve32.sh", "w") as f:
    f.write(text)
print("Updated serve32.sh successfully!")
