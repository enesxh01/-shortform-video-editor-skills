#!/usr/bin/env python3
"""Local-first short-form editor runtime. Requires FFmpeg + ffprobe on PATH."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from fractions import Fraction

VERSION = "0.2.0"
LAYOUTS = {"fullscreen", "split_vertical", "blurred_bars_20_60_20"}

class EditorError(RuntimeError): pass

def run(args, *, capture=True):
    try:
        p = subprocess.run([str(x) for x in args], check=True, text=True,
                           stdout=subprocess.PIPE if capture else None,
                           stderr=subprocess.PIPE if capture else None)
        return p.stdout if capture else ""
    except FileNotFoundError as e:
        raise EditorError(f"Required executable not found: {args[0]}. Install FFmpeg (includes ffprobe).") from e
    except subprocess.CalledProcessError as e:
        raise EditorError(f"Command failed ({e.returncode}): {' '.join(map(str,args))}\n{(e.stderr or '')[-5000:]}") from e

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return "sha256:"+h.hexdigest()

def probe(path):
    p=Path(path).expanduser().resolve()
    if not p.is_file(): raise EditorError(f"Input file does not exist: {p}")
    raw=run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",p])
    data=json.loads(raw)
    streams=data.get("streams",[])
    v=next((s for s in streams if s.get("codec_type")=="video"),None)
    if not v: raise EditorError("Source has no video stream.")
    def rat(x):
        try: return str(Fraction(x))
        except (ValueError,ZeroDivisionError,TypeError): return None
    fmt=data.get("format",{})
    return {"path":str(p),"fingerprint":sha256(p),"duration":float(fmt.get("duration",0)),
      "size_bytes":p.stat().st_size,"format":fmt.get("format_name"),
      "video":{"codec":v.get("codec_name"),"width":v.get("width"),"height":v.get("height"),
        "pixel_format":v.get("pix_fmt"),"frame_rate":rat(v.get("avg_frame_rate")),
        "nominal_frame_rate":rat(v.get("r_frame_rate")),"time_base":rat(v.get("time_base")),
        "start_time":float(v.get("start_time",0) or 0)},
      "audio":[{"codec":s.get("codec_name"),"channels":s.get("channels"),
        "sample_rate":s.get("sample_rate"),"time_base":rat(s.get("time_base")),
        "start_time":float(s.get("start_time",0) or 0)}
        for s in streams if s.get("codec_type")=="audio"]}

def seconds(value):
    if isinstance(value,(int,float)): return float(value)
    s=str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?",s): return float(s)
    parts=s.split(":")
    if len(parts) not in (2,3): raise EditorError(f"Invalid timestamp: {value}")
    try:
        nums=list(map(float,parts))
        if any(n<0 for n in nums) or nums[-1]>=60 or (len(nums)==3 and nums[-2]>=60):
            raise ValueError()
        return nums[-1]+nums[-2]*60+(nums[-3]*3600 if len(nums)==3 else 0)
    except ValueError as e: raise EditorError(f"Invalid timestamp: {value}") from e

def validate(edl, source_info=None):
    errors=[]
    for k in ("schema_version","project_id","source","render","segments","approval"):
        if k not in edl: errors.append(f"Missing top-level field: {k}")
    if errors: return errors
    src=edl["source"]; rnd=edl["render"]; segs=edl["segments"]
    if not src.get("path"): errors.append("source.path is required for rendering")
    if source_info and src.get("fingerprint") and src["fingerprint"] != source_info["fingerprint"]:
        errors.append("Source fingerprint mismatch: EDL does not match the supplied media file")
    if not isinstance(segs,list) or not segs: errors.append("segments must be a non-empty array")
    if rnd.get("container")!="mp4": errors.append("Only MP4 output is currently supported")
    if rnd.get("fps_mode") not in ("cfr","vfr","preserve_native"): errors.append("Invalid fps_mode")
    try:
        w=int(rnd["width"]); h=int(rnd["height"])
        if w<360 or h<640 or w%2 or h%2: errors.append("Output dimensions must be even and at least 360x640")
    except Exception: errors.append("render.width/height must be valid integers")
    if not re.fullmatch(r"\d+/\d+",str(rnd.get("fps_target",""))): errors.append("fps_target must be a rational such as 60/1")
    if edl["approval"].get("status")=="approved" and edl["approval"].get("approved_by_user") is not True:
        errors.append("Approved EDL must have approved_by_user=true")
    for i,s in enumerate(segs):
        label=f"segments[{i}]"
        try:
            a,b=seconds(s["source_in"]),seconds(s["source_out"])
            if b<=a: errors.append(f"{label}: source_out must be after source_in")
            if source_info and b>source_info["duration"]+0.05: errors.append(f"{label}: source_out exceeds source duration")
        except Exception as e: errors.append(f"{label}: {e}")
        if s.get("layout") not in LAYOUTS: errors.append(f"{label}: unsupported layout")
        if s.get("layout")=="split_vertical":
            for key in ("split_top","split_bottom"):
                if not isinstance(s.get(key),dict) or not s[key].get("path"):
                    errors.append(f"{label}: split_vertical requires {key}.path")
        for c in s.get("captions",[]):
            try:
                if seconds(c["end"])<=seconds(c["start"]): errors.append(f"{label}: caption end must follow start")
            except Exception as e: errors.append(f"{label}: invalid caption: {e}")
    return errors

def ass_time(t):
    cs=round(t*100); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def ass_escape(s):
    return str(s).replace("\\","\\\\").replace("{","\\{").replace("}","\\}").replace("\n",r"\N")

def make_ass(edl, path):
    w,h=int(edl["render"]["width"]),int(edl["render"]["height"])
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,{max(34,int(h*.042))},&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,3,1,2,{int(w*.08)},{int(w*.08)},{int(h*.12)},1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events=[]; offset=0.0
    for seg in edl["segments"]:
        start=seconds(seg["source_in"]); end=seconds(seg["source_out"])
        for c in seg.get("captions",[]):
            a=offset+seconds(c["start"]); b=offset+seconds(c["end"])
            if a<offset-0.001 or b>end-start+offset+0.05: continue
            text=ass_escape(c["text"])
            events.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{text}")
        offset+=end-start
    Path(path).write_text(header+"\n".join(events)+"\n",encoding="utf-8")

def render(edl_path, output):
    ep=Path(edl_path).expanduser().resolve()
    edl=json.loads(ep.read_text(encoding="utf-8"))
    source=Path(edl["source"].get("path","")).expanduser().resolve()
    info=probe(source)
    errs=validate(edl,info)
    if errs: raise EditorError("EDL validation failed:\n- "+"\n- ".join(errs))
    if edl["approval"].get("status")=="rejected": raise EditorError("Refusing to render a rejected EDL.")
    if edl["approval"].get("status")!="approved" or not edl["approval"].get("approved_by_user"):
        raise EditorError("Human approval required. Set approval.status=approved and approved_by_user=true only after reviewing the EDL.")
    rnd=edl["render"]; w,h=int(rnd["width"]),int(rnd["height"])
    fps=str(rnd["fps_target"]); target=Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shortform-") as td:
        td=Path(td); ass=td/"captions.ass"; make_ass(edl,ass)
        inputs=["-i",str(source)]
        filters=[]; labels=[]
        has_audio=bool(info["audio"])
        for i,seg in enumerate(edl["segments"]):
            a,b=seconds(seg["source_in"]),seconds(seg["source_out"])
            base=f"[0:v]trim=start={a:.6f}:end={b:.6f},setpts=PTS-STARTPTS"
            layout=seg["layout"]
            if layout=="fullscreen":
                vf=f"{base},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
            elif layout=="blurred_bars_20_60_20":
                # Fill a vertical canvas with a blurred copy; sharp footage occupies the center 60%.
                vf=f"{base},split=2[bg{i}][fg{i}];[bg{i}]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},gblur=sigma=32[blur{i}];[fg{i}]scale={w}:{int(h*.60)}:force_original_aspect_ratio=decrease[sharp{i}];[blur{i}][sharp{i}]overlay=(W-w)/2:(H-h)/2"
            else:
                top=Path(seg["split_top"]["path"]).expanduser().resolve()
                bottom=Path(seg["split_bottom"]["path"]).expanduser().resolve()
                inputs += ["-i",str(top),"-i",str(bottom)]
                ti=1+2*i; bi=ti+1
                vf=f"[{ti}:v]trim=start={seconds(seg['split_top'].get('source_in',0)):.6f}:end={seconds(seg['split_top'].get('source_out',b-a)):.6f},setpts=PTS-STARTPTS,scale={w}:{h//2}:force_original_aspect_ratio=increase,crop={w}:{h//2}[top{i}];[{bi}:v]trim=start={seconds(seg['split_bottom'].get('source_in',0)):.6f}:end={seconds(seg['split_bottom'].get('source_out',b-a)):.6f},setpts=PTS-STARTPTS,scale={w}:{h-h//2}:force_original_aspect_ratio=increase,crop={w}:{h-h//2}[bot{i}];[top{i}][bot{i}]vstack"
                base=""
            if layout=="blurred_bars_20_60_20":
                filters.append(vf+f",setsar=1,fps={fps},format=yuv420p[v{i}]")
            elif layout=="split_vertical":
                filters.append(vf+f",setsar=1,fps={fps},format=yuv420p[v{i}]")
            else: filters.append(vf+f",setsar=1,fps={fps},format=yuv420p[v{i}]")
            labels.append(f"[v{i}]")
        concat="".join(labels)+f"concat=n={len(labels)}:v=1:a=0[vout]"
        filters.append(concat)
        if has_audio:
            for i,seg in enumerate(edl["segments"]):
                a,b=seconds(seg["source_in"]),seconds(seg["source_out"])
                filters.append(f"[0:a:0]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,aresample=async=1:first_pts=0[a{i}]")
            filters.append("".join(f"[a{i}]" for i in range(len(labels)))+f"concat=n={len(labels)}:v=0:a=1[aout]")
        ass_filter_path=str(ass).replace("\\","/").replace(":","\\:").replace("'","\\'")
        filters.append("[vout]subtitles='"+ass_filter_path+"'[vfinal]")
        graph=";".join(filters)
        tmp=td/"render.mp4"
        cmd=["ffmpeg","-hide_banner","-y",*inputs,"-filter_complex",graph,"-map","[vfinal]"]
        if has_audio: cmd += ["-map","[aout]","-c:a","aac","-b:a","192k"]
        else: cmd += ["-an"]
        cmd += ["-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-r",fps,"-fps_mode","cfr","-movflags","+faststart",str(tmp)]
        run(cmd,capture=False)
        qc=probe(tmp)
        if qc["video"]["width"]!=w or qc["video"]["height"]!=h: raise EditorError("QC failed: output dimensions mismatch")
        actual=Fraction(qc["video"]["frame_rate"] or "0/1")
        expected=Fraction(fps)
        if actual!=expected: raise EditorError(f"QC failed: expected {expected} fps, got {actual}")
        run(["ffmpeg","-v","error","-i",str(tmp),"-f","null","-"],capture=True)
        shutil.move(str(tmp),str(target))
        manifest={"status":"technical_qc_passed_human_visual_review_required","output":str(target),
          "output_sha256":sha256(target),"source":info,"output_probe":qc,"ffmpeg_version":run(["ffmpeg","-version"]).splitlines()[0],
          "render_profile":rnd,"segments":len(edl["segments"])}
        target.with_suffix(target.suffix+".manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def main():
    p=argparse.ArgumentParser(description="Local-first short-form video editor runtime")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("inspect",help="Probe and fingerprint source media"); a.add_argument("source"); a.add_argument("--output")
    v=sub.add_parser("validate",help="Validate an EDL"); v.add_argument("edl"); v.add_argument("--source")
    r=sub.add_parser("render",help="Render an approved EDL"); r.add_argument("edl"); r.add_argument("-o","--output",required=True)
    q=sub.add_parser("qc",help="Probe and fully decode an exported video"); q.add_argument("video")
    args=p.parse_args()
    try:
        if args.command=="inspect":
            result=probe(args.source); out=json.dumps(result,indent=2)
            if args.output: Path(args.output).write_text(out,encoding="utf-8")
            print(out)
        elif args.command=="validate":
            edl=json.loads(Path(args.edl).read_text(encoding="utf-8")); info=probe(args.source) if args.source else None
            errs=validate(edl,info)
            print(json.dumps({"valid":not errs,"errors":errs},indent=2)); sys.exit(1 if errs else 0)
        elif args.command=="render":
            print(json.dumps(render(args.edl,args.output),indent=2))
        elif args.command=="qc":
            info=probe(args.video); run(["ffmpeg","-v","error","-i",info["path"],"-f","null","-"])
            print(json.dumps({"decode":"passed","probe":info},indent=2))
    except (EditorError,ValueError,KeyError,json.JSONDecodeError) as e:
        print(f"ERROR: {e}",file=sys.stderr); sys.exit(2)
if __name__=="__main__": main()
