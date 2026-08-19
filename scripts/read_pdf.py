#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pdf_path = "评审系统接口规范_标准版V2.5(1).pdf"

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            print(f"\n===== 第 {i+1} 页 =====")
            print(text)
