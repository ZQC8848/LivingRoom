"""Serial, bounded new sessions. Never joins or terminates a keeper session."""
import asyncio,json,logging
from pathlib import Path
import run_orbis_painting as runner
runner.OUT=Path(__file__).resolve().parent/'motion-v8/generation'
async def main():
    runner.load_keys()
    jobs=json.loads((runner.OUT/'jobs.json').read_text(encoding='utf-8'))
    results=[]
    for job in jobs:
        report_path=runner.OUT/job['id']/'run-v8/report.json'
        if report_path.exists() and json.loads(report_path.read_text())['status']=='captured':continue
        result=await runner.run_job(job,'REACTOR_API_KEY',6,'v8')
        results.append(result)
        if result['status']!='captured':
            # A shared server may be held by another user. Do not compete or
            # reset their session. Finish independent compositing, then retry.
            print('Stopped serial batch after unavailable/failed job.',flush=True)
            break
    (runner.OUT/'batch-report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
if __name__=='__main__':
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
