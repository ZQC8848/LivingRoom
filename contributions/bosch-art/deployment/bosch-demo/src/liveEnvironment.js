import * as THREE from 'three';
// A hard compositing boundary, not an assumed model mask. UVs in the painted
// narrative band sample only the approved plate, regardless of model drift.
export function createLiveEnvironment(plate,mask,live){
 const material=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{uPlate:{value:plate},uMask:{value:mask},uLive:{value:live||plate},uMix:{value:0},uCrop:{value:new THREE.Vector2(48/736,640/736)}},vertexShader:`varying vec3 vDir;void main(){vDir=position;vec4 p=projectionMatrix*vec4(mat3(viewMatrix)*position,1.);gl_Position=p.xyww;}`,fragmentShader:`
 uniform sampler2D uPlate,uMask,uLive;uniform float uMix;uniform vec2 uCrop;varying vec3 vDir;
 vec3 stream(vec2 uv){return sRGBTransferEOTF(texture2D(uLive,vec2(uv.x,uCrop.x+uv.y*uCrop.y))).rgb;}
 void main(){vec3 d=normalize(vDir);vec2 uv=vec2(fract(.5+atan(d.x,-d.z)/6.283185307),.5+asin(clamp(d.y,-1.,1.))/3.141592654);
 vec3 base=texture2D(uPlate,uv).rgb;float a=texture2D(uMask,uv).r*uMix;vec3 video=stream(uv);
 float edge=min(uv.x,1.-uv.x);if(edge<.025)video=mix(stream(vec2(fract(1.-uv.x),uv.y)),video,.5+.5*smoothstep(0.,.025,edge));
 // Flatten only the final polar degrees to avoid equirectangular pinching.
 float pole=smoothstep(.91,.995,abs(d.y));video=mix(video,stream(vec2(.5,uv.y)),pole);
 vec3 col=mix(base,video,a);gl_FragColor=vec4(col,1.);
 #include <colorspace_fragment>
 }`});
 const mesh=new THREE.Mesh(new THREE.SphereGeometry(1,96,48),material);mesh.frustumCulled=false;mesh.renderOrder=-1;return{mesh,material};
}
