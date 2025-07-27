import json
import brotli

def compress():
    ques = open("data/pyqs.questions.json", "r", encoding="utf-8").read()
    chap = open("data/pyqs.chapters.json", "r", encoding="utf-8").read()

    compressed = brotli.compress(ques.encode('utf-8'))
    with open("data/pyqs.questions.json.br", "wb") as f:
        f.write(compressed)

    # compressed = brotli.compress(chap.encode('utf-8'))
    # with open("data/pyqs.chapters.json.br", "wb") as f:
    #     f.write(compressed)

def decompress():
    with open("data/pyqs.questions.json.br", "rb") as f:
        compressed_data = f.read()

    decompressed_data = brotli.decompress(compressed_data)
    ques = json.loads(decompressed_data.decode('utf-8'))
    print(ques[0])
    
compress()