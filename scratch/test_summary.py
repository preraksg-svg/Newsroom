import asyncio
import sys
import os

sys.path.append(os.getcwd())
from backend.llm import generate_ai_summary

title = "Tata Motors EV Sales Hit Record Highs in Q1"
content = "Tata Motors Passenger Vehicles division reports a record expansion in its electric vehicle portfolio, driven by surging demand for Nexon EV, Punch EV, and Tiago EV models across major Indian cities. The company is actively scaling its charging infrastructure partnership networks with public utilities to support the rapid adoption of passenger electric vehicles across both Tier 1 and Tier 2 cities in the country."
sections = [
    {"heading": "Tata EV Strategy", "content": "Tata Motors PV division reports a record expansion in its electric vehicle portfolio, driven by Nexon EV, Punch EV, and Tiago EV."}
]

res = generate_ai_summary(title, content, sections)
print("Result:", res)
