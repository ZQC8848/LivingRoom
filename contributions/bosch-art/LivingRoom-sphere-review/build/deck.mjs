import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import sharp from 'sharp';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const SKILL = 'C:/Users/zoezi/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11011/skills/presentations';
const PYTHON = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe';
const FONT = 'Microsoft YaHei';
const fontPolicy = { basis: 'design', families: [FONT] };
process.env.RUNTIME_NODE_MODULES = 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const concepts = JSON.parse(await fs.readFile(path.join(ROOT, 'concepts.json'), 'utf8'));
const sources = {
 R1: {name:'The End of the World in Four Seasons',artist:'Paul Driessen',url:'https://www.nfb.ca/film/end-of-the-world-in-four-seasons/',fact:'八个相关故事在八个窗口同时展开，四季组织段落',use:'并行线索与共同时间，转成一个全景中的季节与环境关系'},
 R2: {name:'New Book / Nowa książka',artist:'Zbigniew Rybczyński',url:'https://werkleitz.de/en/nowa-ksiazka-new-book',fact:'九格各呈现一个地点，行动把地点联系起来',use:'用一个母题、动作或后果连接整景变化与转头观看'},
 R3: {name:'Video Quartet',artist:'Christian Marclay',url:'https://www.sfmoma.org/artwork/2002.116.A-D/',fact:'四屏电影片段形成视觉与音乐的共同编排',use:'声音引导视线，形状和动作形成节奏上的接力'},
 R4: {name:'The Visitors',artist:'Ragnar Kjartansson',url:'https://www.sfmoma.org/exhibition/ragnar-kjartansson-the-visitors/',fact:'九屏呈现不同房间里共同演奏的音乐家',use:'让环境的不同声源共享一个时间，建立陪伴与共同在场'},
 R5: {name:'Ten Thousand Waves',artist:'Isaac Julien',url:'https://www.isaacjulien.com/projects/ten-thousand-waves/',fact:'多屏编织过去与当代，空间组织观众的观看',use:'让一个环境叠存记忆、距离与不同视角'}
};
const palette={bg:'#F5F3ED',ink:'#172326',muted:'#576565',accent:'#866137',dark:'#111B24',paper:'#F5F0E6'};
const p = Presentation.create({slideSize:{width:1920,height:1080}});
let page=0;
function tx(s,text,x,y,w,h,size=28,color=palette.ink,bold=false,name='') {
 const sh=s.shapes.add({geometry:'textbox',name:name||`text-${s.shapes.items.length}`,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=typeof text==='string'?text.replace(/。$/u,''):text;sh.text.style={typeface:FONT,fontSize:size,bold,color,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};
 return sh;
}
function slide(title,subtitle='') {
 const s=p.slides.add();page++;s.background.fill=palette.bg;
 tx(s,title,64,62,1792,90,62,palette.ink,true,'slide-title');
 if(subtitle)tx(s,subtitle,67,158,1788,66,27,palette.muted,false,'slide-subtitle');
 tx(s,'Living Room  单路 360° 全景体验',66,1023,1050,34,21,palette.muted,false,'footer');
 const n=tx(s,String(page).padStart(2,'0'),1776,1023,80,34,22,palette.muted,false,'page-number');n.text.alignment='right';
 return s;
}
function table(s,values,widths,top,height,fontSize=26) {
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:64,top,width:1792,height,values,columnWidths:widths});
 t.styleOptions={headerRow:false,bandedRows:false};
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:palette.bg,textStyle:{typeface:FONT,fontSize,color:palette.ink},margins:{left:14,right:16,top:14,bottom:12},anchor:'center'});
 t.cells.block({row:0,column:0,rowCount:1,columnCount:values[0].length}).assign({fill:palette.dark,textStyle:{typeface:FONT,fontSize:fontSize,bold:true,color:palette.paper}});
 t.borders.assign({style:'solid',fill:'#D1D2C8',width:1});
 return t;
}
async function image(s,id){
 const src=path.join(ROOT,'assets',`concept-${id}.png`);
 const dst=path.join(HERE,`concept-${id}.jpg`);
 await sharp(src).resize({width:1600,height:1100,fit:'inside',withoutEnlargement:true}).jpeg({quality:89,mozjpeg:true}).toFile(dst);
 const b=await fs.readFile(dst);
 s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/jpeg',alt:`方案 ${id} 的第一人称空间内视角概念图，单路连续全景世界的一个关键帧`,fit:'contain',position:{left:64,top:231,width:1160,height:662}});
}
{
 const s=slide('单路全景的 30 种叙事');s.background.fill=palette.dark;
 for(const sh of s.shapes.items)sh.text.color=palette.paper;
 tx(s,'LIVING ROOM',70,250,1750,115,92,palette.paper,true);
 tx(s,'玩家站在世界之中',73,404,1720,108,72,palette.paper,true);
 tx(s,'30 个叙事与互动方案\n每个方案配空间内视角概念图',76,571,1550,145,40,'#D8D3C5');
 tx(s,'斯坦福 Immerse the Bay 项目评审稿',76,825,1600,50,30,'#BBAA8A');
 tx(s,'按 2026 年 11 月 14 日确认的新规格设计',76,892,1600,42,25,'#BBAA8A');
 s.speakerNotes.text='任务规格：仅一条全景视频映射到内向球面，玩家原地转头观看。旧版六面独立视频方案不在本稿范围内。全部为原创设计提案，图像由内置 image_gen 生成。不是现有原型运行截图，也不是已经验证的实时生成结果。';
}
{
 const s=slide('五部参考作品的叙事方法','作品结构提供设计启发，30 个方案均为原创提案');
 const values=[['参考','作品','原作结构','在单路全景中的转译'],...Object.entries(sources).map(([id,r])=>[id,r.name+'\n'+r.artist,r.fact,r.use])];
 table(s,values,[100,620,470,602],248,690,25);
 s.speakerNotes.text=Object.entries(sources).map(([id,r])=>`${id} ${r.name}\n${r.url}\n作品事实：${r.fact}\n设计推演：${r.use}`).join('\n\n');
}
{
 const s=slide('单路全景的观看方式','一条连续影像包围玩家，叙事通过观看方向与整景变化展开');
 const rows=[
 ['转头完成剪辑','用声音、光和运动邀请转头。让关键事件持续到玩家有机会看见。'],
 ['环境呈现因果','一次触碰引起可辨认的回应，随后让变化传播或演变为下一段风景。'],
 ['上下关系揭示身份','抬头与低头用于发现海面、天空、倒影或痕迹，让身体参与理解。'],
 ['共同时间组织段落','季节、天气、光和声音维持整体节奏，风景可以在一条影片里逐步改写。'],
 ['选择留下痕迹','结尾保留玩家关注过的颜色、物件或状态，让互动具有可感知的后果。']
 ];
 rows.forEach((r,i)=>{tx(s,r[0],78,265+i*127,440,60,36,palette.accent,true);tx(s,r[1],570,269+i*127,1245,90,31);});
 tx(s,'图示说明：概念图呈现玩家朝一个方向看到的关键帧，完整环绕关系由每页文字补充。',80,945,1740,54,25,palette.muted);
 s.speakerNotes.text='以下原则为本项目的设计推演。前景、环绕、头顶、脚下指单个全景画面中的观看区域，并非独立视频或屏幕。所有互动表现仍需用当前生成链路验证。';
}
{
 const s=slide('30 个方案索引','按主要叙事方法分组，同一方案可以借鉴多部作品');
 const fam=[...new Set(concepts.map(c=>c.family))];
 const values=[['方向','方案'],...fam.map(f=>[f,concepts.filter(c=>c.family===f).map(c=>c.id+' '+c.title).join('　　')])];
 table(s,values,[290,1502],245,706,28);
 s.speakerNotes.text=concepts.map(c=>`${c.id} ${c.title}：${c.premise}`).join('\n');
}
const maxConcepts=process.argv.includes('--sample')?1:30;
for(const c of concepts.slice(0,maxConcepts)){
 const s=slide(`${c.id}  ${c.title}`,`${c.family}　　${c.grammar}`);
 await image(s,c.id);
 tx(s,'故事',1288,238,560,36,24,palette.accent,true);
 tx(s,c.premise,1288,281,560,111,29);
 tx(s,'玩家互动',1288,414,560,36,24,palette.accent,true);
 tx(s,c.interaction,1288,457,560,128,28);
 tx(s,'空间内的观看',1288,606,560,36,24,palette.accent,true);
 tx(s,c.spatial.join('\n'),1288,649,560,126,25);
 tx(s,'结尾的变化',1288,798,560,36,24,palette.accent,true);
 tx(s,c.reveal,1288,841,560,104,28);
 tx(s,'视觉风格：'+c.style,68,910,1150,54,25,palette.muted);
 tx(s,'先验证：'+c.test,68,967,1760,39,23,palette.muted);
 s.shapes.items.find(x=>x.name==='footer').text=`参考 ${c.refs.join('、')}　　生成概念图，非原型截图`;
 s.speakerNotes.text=[`方案 ${c.id} ${c.title}`,`单路360°全景视频，玩家在球面内部观看。不是六路视频或六面分屏。`,
 `叙事结构：${c.grammar}`,`故事：${c.premise}`,`互动：${c.interaction}`,`空间：${c.spatial.join('；')}`,`结尾：${c.reveal}`,`视觉风格：${c.style}`,`先验证：${c.test}`,
 '建议体验段落：',...c.beats.map((b,i)=>`${i+1}. ${b}`),'参考来源：',...c.refs.map(id=>`${id} ${sources[id].name} ${sources[id].url}`),
 `图像：内置 image_gen 生成的原创设计关键帧。该单帧不是可播放的全景贴图，也不是已验证的模型输出。\n图像提示词：${c.id==='01'?await fs.readFile(path.join(HERE,'prompt-01.txt'),'utf8').catch(()=>c.art):(await fs.readFile(path.join(HERE,'prompt-base.txt'),'utf8').catch(()=>''))+c.art}`].join('\n\n');
}
{
 const s=slide('第一轮评审','每个方案可直接评论：保留、待定或放弃，并写一句原因');
 const prompts=[
 ['故事为何需要全景','转头、回看、抬头或低头，是否让故事获得新的意思？'],
 ['互动是否改变体验','玩家行动的结果是否可看见，是否影响最后留下的风景？'],
 ['哪一刻最想进入','从概念图中选择真正想置身其中的瞬间，再检查其叙事作用。'],
 ['先深化哪些编号','建议先挑 3 至 5 个方向，再为入选方案绘制连续关键帧与体验脚本。']
 ];
 prompts.forEach((r,i)=>{tx(s,r[0],85,280+i*151,520,70,38,palette.accent,true);tx(s,r[1],665,284+i*151,1120,100,33);});
 tx(s,'编号可以混合：保留一个方案的故事，也可以采用另一个方案的视觉或互动方式。',85,929,1730,60,28,palette.muted);
 s.speakerNotes.text='本页为评审建议，没有对尚未实测的互动效果给出评分。优先按体验价值挑选，再由工程师评估具体实现。';
}
{
 const s=slide('来源与图示范围','参考作品的结构与原创方案的设计推演分开记录');
 Object.entries(sources).forEach(([id,r],i)=>{const sh=tx(s,`${id}  ${r.name}\n${r.artist}`,85,252+i*112,1740,95,30);sh.hyperlink={uri:r.url,isExternal:true};});
 tx(s,'原型参考：ZQC8848/LivingRoom；本稿按用户确认的单路球面全景新规格设计。',85,837,1730,65,27,palette.muted);
 tx(s,'概念图为生成的空间内视角单帧。叙事与互动是提案，尚未代表可直接播放的全景素材或实时效果。',85,917,1730,76,27,palette.muted);
 s.speakerNotes.text=Object.entries(sources).map(([id,r])=>`${id} ${r.name}\n${r.url}`).join('\n\n')+'\n\n原型：https://github.com/ZQC8848/LivingRoom\n审阅代码版本：59e5cf8。原型的六面布局已被用户的新规格覆盖，本稿没有沿用六路视频拓扑。\n全部概念图为内置 image_gen 生成的原创关键帧，无参考作品剧照。';
}

await fs.mkdir(path.join(HERE,'renders'),{recursive:true});
await fs.writeFile(path.join(HERE,'deck.json'),JSON.stringify(p.toProto()));
await fs.writeFile(path.join(HERE,'slide-map.json'),JSON.stringify(p.slides.items.map((s,i)=>({index:i+1,id:s.id,title:s.shapes.items.find(x=>x.name==='slide-title')?.text?.toString?.()})),null,2));
const indexes=process.argv.includes('--sample')?[0,1,2,3,4,5,6]:p.slides.items.map((_,i)=>i);
for(const i of indexes){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:0.8});
 await fs.writeFile(path.join(HERE,'renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
 console.log('rendered',i+1);
}
if(process.argv.includes('--sample')){console.log('sample done');process.exit(0);}
const candidatePath=path.join(HERE,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidatePath);
console.log('exported candidate',candidatePath);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(ROOT,'output','Living-Room-30-Panoramic-Concepts.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath,finalPath,pythonExecutable:PYTHON,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','18288000,10287000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','2','--require-native-table-slide','4'],explicitTotalSlideCount:36,requiredNativeTableOwnerSlides:[2,4],fontPolicy,verifyArtifactToolImport:true,receiptPath:path.join(HERE,'validation.json')});
console.log(JSON.stringify(result));
