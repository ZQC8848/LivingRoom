from pathlib import Path
import json,cv2,numpy as np
ROOT=Path(__file__).resolve().parent
REF=ROOT/'references'
def prepare():
    day=cv2.imread(str(REF/'day-original.png'));night=cv2.imread(str(REF/'night-imagegen.png'))
    if day.shape!=night.shape:raise ValueError('Reference dimensions differ')
    for label,im in [('day',day),('night',night)]:
        art=cv2.resize(im,(1280,640),interpolation=cv2.INTER_AREA)
        canvas=np.empty((736,1280,3),np.uint8)
        canvas[:48]=np.median(art[:12],axis=(0,1));canvas[48:688]=art;canvas[688:]=np.median(art[-12:],axis=(0,1))
        cv2.imwrite(str(REF/f'{label}-contained.png'),canvas)
    # Analysis only: geometry checks do not alter the edited night image.
    sift=cv2.SIFT_create(nfeatures=6000,contrastThreshold=.012)
    gray=[cv2.createCLAHE(2,(8,8)).apply(cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)) for im in (day,night)]
    keys=[sift.detectAndCompute(im,None) for im in gray]
    pairs=cv2.BFMatcher().knnMatch(keys[0][1],keys[1][1],k=2)
    good=[a for a,b in pairs if a.distance<.72*b.distance]
    a=np.float32([keys[0][0][m.queryIdx].pt for m in good]);b=np.float32([keys[1][0][m.trainIdx].pt for m in good])
    mat,inl=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2)
    d=np.linalg.norm(a-b,axis=1);inside=inl.ravel()>0
    report={'dimensions':[day.shape[1],day.shape[0]],'matches':len(good),'inliers':int(inside.sum()),
            'estimated_affine':mat.tolist(),'median_inlier_displacement_pixels':float(np.median(d[inside])),
            'p95_inlier_displacement_pixels':float(np.quantile(d[inside],.95)),
            'note':'Imagegen edited night reference, no geometry warping applied. These matched features are a proxy, not a guarantee for every silhouette.'}
    (ROOT/'reference-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
if __name__=='__main__':prepare()
