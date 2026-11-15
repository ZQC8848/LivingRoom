from pathlib import Path
import shutil
r=Path(__file__).resolve().parent
s=(r/'compose_bosch_v7.py').read_text()
s=s.replace("OUT=ROOT/'orbis-test/delivery-v4'","OUT=ROOT/'orbis-test/delivery-v5'")
s=s.replace('from analyze_orbis_painting import registration','from analyze_orbis_painting import registration\nfrom bosch_marked_motion import MarkedMotion')
s=s.replace('    water=water_setup(garden);fire=prepare_fire(hell)','''    for tr in trees:
        if tr['name']=='far-left':
            x0,y0,x1,y1=tr['box'];treeplate[y0:y1,x0:x1]=garden[y0:y1,x0:x1]
    trees=[tr for tr in trees if tr['name']!='far-left']
    marked=MarkedMotion(garden,hell)
    water=water_setup(garden);fire=prepare_fire(hell)''')
s=s.replace('        strips.append(np.uint8(np.clip(np.round(frame),0,255)))','''        frame=marked.render(frame,'garden',phase)
        frame[protected]=garden[protected]
        strips.append(np.uint8(np.clip(np.round(frame),0,255)))''')
s=s.replace('f[y0:y1,x0:x1]=p;hellstrips.append(np.uint8(np.clip(np.round(f),0,255)))',"""f[y0:y1,x0:x1]=p
        f=marked.render(f,'hell',phase)
        hellstrips.append(np.uint8(np.clip(np.round(f),0,255)))""")
s=s.replace('    metrics.update(architecture_changed_pixels_before_encoding=',"""    metrics['marked_motion_catalog']='art-lab/motion-v8/motion-catalog.json'
    metrics['new_marked_regions']=51
    metrics.update(architecture_changed_pixels_before_encoding=""")
(r/'compose_bosch_v8.py').write_text(s)
out=r/'orbis-test/delivery-v5';out.mkdir(exist_ok=True)
for f in ['bird-object-cache.npz','fire-object-cache.npz']:shutil.copy2(r/'orbis-test/delivery-v4'/f,out/f)
print('Versioned compositor ready.')
