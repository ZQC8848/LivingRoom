from pathlib import Path
import shutil
r=Path(__file__).resolve().parent
s=(r/'compose_bosch_v8.py').read_text()
s=s.replace('from bosch_marked_motion import MarkedMotion','from bosch_marked_motion_v9 import MarkedMotion')
s=s.replace("OUT=ROOT/'orbis-test/delivery-v5'","OUT=ROOT/'orbis-test/delivery-v6'")
s=s.replace("metrics['marked_motion_catalog']='art-lab/motion-v8/motion-catalog.json'","metrics['marked_motion_catalog']='art-lab/motion-v9/motion-catalog.json'\n    metrics['intentionally_static']=['G03']\n    metrics['revision']='r4 complete silhouettes, downward falling water, stronger rising fire/smoke'")
s=s.replace("metrics['new_model_calls']=len(review)","metrics['new_model_calls']=0\n    metrics['prior_model_captures_reused']=len(review)")
s=s.replace("metrics['method']='original-paint object RGBA rigs; registered bounded Orbis motion fields for herd, stag, bank bird and bathers; retained Orbis foreground bird and fire; authored wind, waterfall, floating objects, both rivers and horizon smoke'","metrics['method']='complete hand-polygon original-paint sky objects; joined bird-wing articulation; original G03 held static; downward advected water and falling droplets; stronger rising fire and smoke; retained v7 horse and accepted prior motion outside corrected regions'")
s=s.replace("metrics['notes']='New model RGB was rejected for exposure drift and weak articulation. Four generated motion fields are applied only to isolated original-paint cutouts, bounded to 2.5 pixels. Source wing and leg rigs supplement those fields. Sky, ground, buildings and camera remain anchored. Native generated loops are not claimed.'","metrics['notes']='User-reviewed correction. Complete object polygons intentionally include narrow safe background margins. No color-key holes through figures, mounts, fish tails, ornament wings or feet. Corrected regions use original paint with coherent articulation; G03 is intentionally static. Water falls down, smoke rises up. No camera movement. Not a physical fluid simulation or model-native loop.'")
(r/'compose_bosch_v9.py').write_text(s)
out=r/'orbis-test/delivery-v6';out.mkdir(exist_ok=True)
for f in ['bird-object-cache.npz','fire-object-cache.npz']:shutil.copy2(r/'orbis-test/delivery-v4'/f,out/f)
print('Prepared corrected compositor, preserving previous releases.')
