"""User's red marks are a specification, never an input texture to the model."""
from pathlib import Path
import json
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'motion-v8'; GEN=OUT/'generation'; GEN.mkdir(parents=True,exist_ok=True)
items=[]
def add(id,layer,box,action,method='cutout',**kw):
    items.append(dict(id=id,layer=layer,box=box,action=action,method=method,**kw))
add('G01','garden',[61,103,190,245],'Flying pose, wing/fins flap; stay in the same location','orbis',job='aerial-creature')
add('G02','garden',[449,134,550,208],'Boat gently floats up and down')
add('G03','garden',[617,157,664,220],'Translucent wing gently flutters')
add('G04','garden',[954,126,1233,197],'Distant birds flap with small bounded flight','flock')
add('G05','garden',[1092,234,1167,275],'Roof fish gently rocks, building fixed')
add('G06','garden',[1566,121,1631,210],'Suspended ornament gently floats')
add('G07','garden',[1649,199,1715,291],'Two birds flap in the same small area','orbis',job='sky-birds')
for id,box in [('G08',[120,285,202,417]),('G09',[370,334,470,388]),('G10',[0,383,85,490]),('G12',[533,381,650,430]),('G15',[477,516,545,582]),('G24',[1692,306,1774,425]),('G25',[0,587,182,724]),('G26',[179,675,281,762]),('G27',[978,712,1063,786]),('G28',[1095,745,1198,816]),('G29',[1367,620,1453,705]),('G30',[1507,578,1563,666]),('G31',[1652,579,1774,715]),('G32',[1446,756,1525,845]),('G33',[1512,704,1598,789]),('G34',[1621,694,1692,768]),('G35',[552,234,579,268]),('G36',[561,273,603,311]),('G37',[724,229,766,266]),('G38',[724,265,766,300])]:
    add(id,'garden',box,'Wind moves foliage; roots and buildings remain fixed','wind')
add('G11','garden',[421,401,534,461],'Deer make small slow steps inside this patch','orbis',job='herd')
add('G13','garden',[558,436,612,488],'Strawberry gently squashes and stretches')
add('G14','garden',[407,474,481,549],'Bank bird makes a small wing ruffle','orbis',job='bank-bird')
add('G16','garden',[636,504,757,565],'Long neck gently sways, body stays near the bank')
add('G17','garden',[760,372,826,578],'Left fountain flows downward','waterfall')
add('G18','garden',[943,371,1033,578],'Right fountain flows downward','waterfall')
add('G19','garden',[1071,460,1120,511],'Small waterbird ruffles its wings','orbis',job='waterbird-small')
add('G20','garden',[1034,502,1107,562],'Large waterbird makes a small half flap','orbis',job='waterbird-large')
add('G21','garden',[1174,415,1221,456],'Stag makes small planted steps','orbis',job='stag')
add('G22','garden',[1168,448,1338,495],'Bathers make small head and arm gestures in the pool','orbis',job='bathers')
add('G23','garden',[1129,600,1225,649],'Fish gently bobs in the water')
add('G39','garden',[77,370,131,409],'Small figures walk slowly within the group','puppet')
add('H01','hell',[451,137,548,209],'Boat floats up and down; small wing flutter')
add('H02','hell',[953,118,1174,209],'Dark birds fly with small bounded displacement','flock')
add('H03','hell',[1564,121,1632,212],'Suspended ornament gently floats')
add('H04','hell',[62,367,101,410],'Two small figures take slow small steps','puppet')
for i,box in enumerate([[0,253,106,326],[383,270,440,334],[458,249,545,325],[749,276,837,338],[938,273,1020,339],[1247,246,1370,331],[1624,235,1746,328]],5):
    add(f'H{i:02}','hell',box,'Flames lick behind a fixed skyline; smoke drifts upward','fire-smoke')
add('H12','hell',[0,425,1774,691],'Dark river and pools ripple with moving fire reflections','water')
items.sort(key=lambda x:x['id'])
(OUT/'motion-catalog.json').write_text(json.dumps({'source_dimensions':[1774,887],'camera':'locked; no movement','period_seconds':8,'items':items,'retained':['fixed painted horse muzzle and horn','Orbis blue foreground bird','existing tree cutouts','garden whole-river ripples','keyed central-right Orbis fire'],'annotations_are_not_model_inputs':True},ensure_ascii=False,indent=2),encoding='utf-8')

actions={
 'aerial-creature':'Only the small flying creature in the upper left flexes its two leaf-like wings twice in a gentle but clearly visible flying pose. It stays at the same position. Its rider and the tree remain attached and still. No forward flight.',
 'sky-birds':'Only the blue bird and the small pale bird in the upper-right sky make one slow, visible wingbeat, then return to their original wing positions. Each bird stays in the same small patch of sky.',
 'herd':'Only the little group of deer makes tiny slow alternating steps and one small head turn. The herd remains together within its original grassy patch. All antlers, heads and bodies retain their original shapes.',
 'bank-bird':'Only the small blue bird-like creature beside the bank makes one visible folded-wing ruffle and settles. Its beak and head stay the same, its feet stay near their original positions.',
 'waterbird-small':'Only the SMALL upper waterbird near the right shore makes one modest wing ruffle. Its long neck and beak remain unchanged. Its body remains at the same location. The larger bird below it stays completely still.',
 'waterbird-large':'Only the LARGE lower waterbird by the right shore opens its visible folded wing slightly, then closes it slowly. Its head, beak and neck stay unchanged. The smaller bird above remains completely still.',
 'stag':'Only the little antlered deer behind the pool makes two slow tiny alternating steps without leaving its grassy patch. Its antlers and face retain their original shape.',
 'bathers':'Only the five tiny painted bathers in the pool make a gentle head turn, a small arm gesture and a slight shift of weight. They remain in the pool at the same positions. This is a quiet museum painting tableau with nonsexual classical art figures.',
}
jobs=[]
for it in items:
    if it['method']!='orbis':continue
    im=Image.open(ROOT/'bosch-world-assets'/f'{it["layer"]}-generated.png').convert('RGB')
    x0,y0,x1,y1=it['box']; cx=(x0+x1)/2;cy=(y0+y1)/2
    cw=max((x1-x0)*1.8,(y1-y0)*1.8*16/9,320);ch=cw*9/16
    cx=max(cw/2,min(1774-cw/2,cx));cy=max(ch/2,min(887-ch/2,cy))
    crop=list(map(round,[cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2]))
    job=dict(id=it['job'],layer=it['layer'],source_pixels=[1774,887],crop=crop,box=it['box'],action=actions[it['job']],model='reactor/visko-orbis-dynamic')
    job['prompt']='A flat early-Netherlandish painted tableau. Static camera, absolutely locked framing, no camera movement, no zoom, no pan, no parallax. '+job['action']+' Keep the exact original painted colors, brushwork, lighting and composition. All buildings, banks, trees, grass, water and other figures are motionless and unchanged. Small bounded motion with an unchanged background. No added objects, no mouth changes, no glowing highlights. End near the original pose.'
    folder=GEN/job['id'];folder.mkdir(exist_ok=True)
    im.crop(crop).resize((1024,576),Image.Resampling.LANCZOS).save(folder/'reference.png')
    mask=Image.new('L',im.size); ImageDraw.Draw(mask).rectangle([x0-8,y0-8,x1+8,y1+8],fill=255)
    mask.crop(crop).resize((1024,576)).save(folder/'context-mask.png')
    (folder/'prompt.txt').write_text(job['prompt'],encoding='utf-8'); jobs.append(job)
(GEN/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared',len(items),'marked regions and',len(jobs),'clean-reference model jobs.')
