"""Self-Boosting LAM LoRA Fine-Tuning Module.

Implements Module 6: Self-Boosting LAM Training.
Performs Parameter-Efficient Fine-Tuning (PEFT) using LoRA on harvested FSM repair
trajectories, internalizing the UNDERSTAND->COLLECT->TRY_FIX->REFLECT policy.
"""

import os
import sys

# Ensure allocation config and default GPU are set before importing PyTorch
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
if "CUDA_VISIBLE_DEVICES" not in os.environ:
    os.environ["CUDA_VISIBLE_DEVICES"] = "1"

import argparse
from pathlib import Path
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = os.path.expanduser("~/btp/models/qwen32b-gptq")
DATA_DIR = ROOT / "repairlam" / "training" / "data"
OUTPUT_DIR = os.path.expanduser("~/btp/models/repairlam-qwen32b-lora")


def format_prompts(batch, tokenizer):
    texts = []
    for messages in batch["messages"]:
        # Standard chat template formatting
        formatted = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        texts.append(formatted)
    return {"text": texts}


def train(model_path=DEFAULT_MODEL_PATH, output_dir=OUTPUT_DIR, gpu_id=1, epochs=3, lr=2e-5, max_length=2048):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    print(f"--- Training LoRA Adapter on GPU {gpu_id} ---")
    print(f"Base model: {model_path}")
    print(f"Output directory: {output_dir}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    train_file = DATA_DIR / "sft_train.jsonl"
    val_file = DATA_DIR / "sft_val.jsonl"
    if not train_file.exists():
        raise FileNotFoundError(f"Training data not found at {train_file}. Run harvest.py first!")

    raw_dataset = load_dataset("json", data_files={
        "train": str(train_file),
        "validation": str(val_file)
    })

    print(f"Loaded dataset: {len(raw_dataset['train'])} train, {len(raw_dataset['validation'])} val")

    def tokenize_fn(examples):
        texts = []
        for msgs in examples["messages"]:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)
            texts.append(text)
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=max_length,
            padding=False,
            return_tensors=None
        )
        tokenized["labels"] = tokenized["input_ids"].copy()
        return tokenized

    tokenized_dataset = raw_dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=raw_dataset["train"].column_names
    )

    print("Loading base model in half precision (fp16)...")
    # V100 is Volta (sm_70); use torch.float16, no bf16
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )

    model = get_peft_model(model, lora_config)
    model.enable_input_require_grads()
    model.print_trainable_parameters()

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        gradient_checkpointing=True,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        fp16=True,
        bf16=False,
        logging_steps=5,
        save_total_limit=2,
        dataloader_num_workers=0,
        report_to="none"
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True,
        pad_to_multiple_of=8
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        data_collator=data_collator
    )

    print("Starting fine-tuning...")
    train_result = trainer.train()

    print(f"Saving fine-tuned adapter to {output_dir}...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)
    print("LoRA Fine-tuning completed successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--out", default=OUTPUT_DIR)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max_length", type=int, default=2048)
    args = parser.parse_args()

    train(model_path=args.model, output_dir=args.out, gpu_id=args.gpu,
          epochs=args.epochs, lr=args.lr, max_length=args.max_length)
