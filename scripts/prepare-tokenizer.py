from transformers import T5Tokenizer

T5Tokenizer.from_pretrained('t5-11b', model_max_length=2048)
