import os
import torch

os.environ["CUDA_VISIBLE_DEVICES"] = "1"
print("Testing model load on GPU 1...")

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, TaskType

model_path = "/home/23ucs603/btp/models/qwen32b-gptq"

try:
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    print("Tokenizer loaded successfully.")
    
    # Try loading config first
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    print("Model loaded successfully. Type:", type(model))
    
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    
    peft_model = get_peft_model(model, lora_config)
    peft_model.print_trainable_parameters()
    print("PEFT LoRA setup verified successfully!")
except Exception as e:
    import traceback
    print("Error during test:")
    traceback.print_exc()
