import * as THREE from 'three';
// A hard compositing boundary, not an assumed model mask. UVs in the painted
// narrative band sample only the approved plate, regardless of model drift.
export function createLiveEnvironment(plate,mask,live){
 const material=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{uPlate:{value:plate},uMask:{value:mask},uLive:{value:live||plate},uMix:{value:0},uCrop:{value:new THREE.Vector2(48/736,640/736)},uRelight:{value:1},uLightGain:{value:1},uLightTint:{value:new THREE.Vector3(1,1,1)},uSkyGrade:{value:new THREE.Vector3(1,1,1)},uGroundGrade:{value:new THREE.Vector3(1,1,1)},uSkyPole:{value:new THREE.Vector3(.13,.15,.13)},uGroundPole:{value:new THREE.Vector3(.1,.12,.025)},uSkyLuma:{value:.3}},vertexShader:`varying vec3 vDir;void main(){vDir=position;vec4 p=projectionMatrix*vec4(mat3(viewMatrix)*position,1.);gl_Position=p.xyww;}`,fragmentShader:`
 uniform sampler2D uPlate,uMask,uLive;uniform float uMix,uRelight,uLightGain,uSkyLuma;uniform vec3 uLightTint,uSkyGrade,uGroundGrade,uSkyPole,uGroundPole;uniform vec2 uCrop;varying vec3 vDir;
 vec3 stream(vec2 uv){return sRGBTransferEOTF(texture2D(uLive,vec2(uv.x,uCrop.x+uv.y*uCrop.y))).rgb;}
 void main(){vec3 d=normalize(vDir);vec2 uv=vec2(fract(.5+atan(d.x,-d.z)/6.283185307),.5+asin(clamp(d.y,-1.,1.))/3.141592654);
 vec3 base=texture2D(uPlate,uv).rgb;float a=texture2D(uMask,uv).r*uMix;vec3 video=stream(uv);
 float edge=min(uv.x,1.-uv.x);if(edge<.025)video=mix(stream(vec2(fract(1.-uv.x),uv.y)),video,.5+.5*smoothstep(0.,.025,edge));
 // Grade the model's opening to the approved material colours. Subsequent
 // changes remain model-driven, with separate calibration for sky and ground.
 video*=uv.y>.5?uSkyGrade:uGroundGrade;
 // A single averaged pole colour avoids replaying one vertical cloud column
 // around the zenith, which made the old concentric dome ring.
 float pole=smoothstep(.82,.985,abs(d.y));video=mix(video,d.y>0.?uSkyPole:uGroundPole,pole);
 // Broad shadows follow generated cloud brightness; no geometry/UV displacement.
 vec2 c=vec2(uv.x,.77);vec3 cloud=(stream(c)+stream(c+vec2(.045,0.))+stream(c-vec2(.045,0.))+stream(c+vec2(0.,.035))+stream(c-vec2(0.,.035)))/5.;
 float relativeCloud=clamp(dot(cloud,vec3(.2126,.7152,.0722))/max(uSkyLuma,.02)-1.,-.4,.4);
 float shadow=1.+relativeCloud*.12*(1.-smoothstep(.4,.7,uv.y));
 vec3 lit=base*uLightGain*uLightTint*shadow;
 base=mix(base,lit,uRelight*uMix);
 vec3 col=mix(base,video,a);gl_FragColor=vec4(col,1.);
 #include <colorspace_fragment>
 }`});
 const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,96,48),material);mesh.frustumCulled=false;mesh.renderOrder=-1;return{mesh,material};
}
