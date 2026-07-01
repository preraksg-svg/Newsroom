import asyncio
import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from layer3_generation.generation_fanout import run_microtask_a_with_retry, validate_zapway_voice

async def main():
    # Load dotenv if available to get GROQ_API_KEY
    from dotenv import load_dotenv
    load_dotenv()
    
    print("==================================================")
    print("TESTING ZAPWAY VOICE MANIFEST & SELF-CORRECTION")
    print("==================================================")
    
    # Raw PR-heavy content simulation
    pr_content = """
    We are thrilled to share that Rivian has achieved exceptional performance this quarter.
    Our team is proud to announce that our Normal, Illinois facility delivered 12,640 vehicles.
    We are excited to share that we are staying up-to-date and remain committed to our mission.
    #Rivian #Sustainability is our core focus.
    """
    
    print("Input PR-heavy content:")
    print(pr_content.strip())
    print("\nTriggering run_microtask_a_with_retry...")
    
    # Run the generator task
    result = await run_microtask_a_with_retry(pr_content, url="http://example.com/rivian-pr")
    
    print("\nResult Payload:")
    import pprint
    pprint.pprint(result)
    
    # Run voice validator on final result
    voice_violations = validate_zapway_voice(result)
    print(f"\nFinal Voice Violations Count: {len(voice_violations)}")
    if voice_violations:
        print("Violations detected:")
        for v in voice_violations:
            print(f"- {v['type']} violation at {v['path']}: {v['violating_text']}")
        sys.exit(1)
    else:
        print("SUCCESS: Zero first-person pronouns or marketing fluff detected in final output!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
