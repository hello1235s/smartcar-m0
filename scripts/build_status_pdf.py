"""Host-side Chinese status document from measured summary JSON."""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Preformatted,KeepTogether


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--summary',required=True); parser.add_argument('--out',required=True); a=parser.parse_args()
    data=json.loads(Path(a.summary).read_text(encoding='utf-8')); dest=Path(a.out); dest.parent.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('SC','C:/Windows/Fonts/simhei.ttf'))
    navy=colors.HexColor('#123243'); teal=colors.HexColor('#0c807d'); muted=colors.HexColor('#526877'); light=colors.HexColor('#edf4f6')
    styles={
      'title':ParagraphStyle('title',fontName='SC',fontSize=23,leading=30,textColor=navy,spaceAfter=7),
      'heading':ParagraphStyle('heading',fontName='SC',fontSize=14,leading=20,textColor=teal,spaceBefore=12,spaceAfter=8),
      'body':ParagraphStyle('body',fontName='SC',fontSize=10,leading=15,textColor=navy,spaceAfter=7,wordWrap='CJK'),
      'small':ParagraphStyle('small',fontName='SC',fontSize=8.5,leading=12,textColor=muted,spaceAfter=6,wordWrap='CJK'),
      'cell':ParagraphStyle('cell',fontName='SC',fontSize=9,leading=12,textColor=navy,wordWrap='CJK'),
      'headcell':ParagraphStyle('headcell',fontName='SC',fontSize=9,leading=12,textColor=colors.white,wordWrap='CJK'),
      'code':ParagraphStyle('code',fontName='Courier',fontSize=8.7,leading=13,textColor=navy,backColor=light,borderPadding=10),
    }
    story=[]
    def p(text,kind='body'): return Paragraph(text,styles[kind])
    def table(rows,widths,status=False):
        rendered=[[p(escape(str(v)),'headcell' if i==0 else 'cell') for v in row] for i,row in enumerate(rows)]
        t=Table(rendered,colWidths=widths,repeatRows=1,hAlign='LEFT'); commands=[('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.5,navy),('LINEBELOW',(0,1),(-1,-1),.4,colors.HexColor('#d9e4e9'))]
        for i in range(1,len(rows)):
            if i%2==0: commands.append(('BACKGROUND',(0,i),(-1,i),colors.HexColor('#f5f8fa')))
            if status: commands.append(('BACKGROUND',(1,i),(1,i),colors.HexColor('#e8f5ee') if i<=12 else colors.HexColor('#fff1d7')))
        t.setStyle(TableStyle(commands)); return t
    width=A4[0]-80
    story+=[p('智能车训练验收状态','title'),p('M1 / M3 / M5 / M6  |  张驰  |  '+data['created'],'small'),p('USB 摄像头和麦克风已打通。M1、M3与M5的软件验证已完成；M6保留板端、赛道精度和未达性能阈值。')]
    cards=[['M1：4项已验','M3：4项已验','M5：软件已验','M6：工程已验 / 待板端']]
    card=Table([[p(x,'cell') for x in cards[0]]],colWidths=[width/4]*4); card.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),light),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#c8dce3')),('TOPPADDING',(0,0),(-1,-1),11),('BOTTOMPADDING',(0,0),(-1,-1),11)])); story+=[card,Spacer(1,12)]
    rows=[['编号','状态','已验证内容 / 尚未达标处'],
      ['M1-1','已验','三节点链路、接口、滤波、动态参数和服务超时。'],
      ['M1-2','已验','双命名空间六节点、参数隔离、就绪后启动及错误提示。'],
      ['M1-3','已验','两组K/外参、ATS扫参、投影图、TF及仿真时钟切换录像。'],
      ['M1-4','已验','31.72 FPS，控制约21 Hz，P95约26.71 ms，像素语义一致。'],
      ['M3-1','已验','10次2m圆角方形；odom与仿真真值CSV、误差统计及TF图。'],
      ['M3-2','已验','自建环形世界、标准SLAM地图、0.95m窄门、历史回访图约束。'],
      ['M3-3','已验','3次成功2次，66.7%达到60%；路线超过12m并含转弯。'],
      ['M3-4','已验','三组各10次；成功率80% / 30% / 调优70%，四指标与失效边界。'],
      ['M5-1','已验','纯Python任务内核、30项节点契约测试、可替换ROS后端。'],
      ['M5-2','已验','10Hz DDS聚合、5Hz网页、告警、离线导出及实际资源采样。'],
      ['M5-3','已验','真实KEY/麦克风、锁存急停、模型热切、软/硬复位和审计链。'],
      ['M5-4','已验','五场ROS软件任务、MCAP复盘、实验晋升和跨系统基线自验。'],
      ['M6-1','板端待验','ONNX17与动态batch、CPU60秒、真实USB录像已验；Orin未到。'],
      ['M6-2','精度/倍率待补','三种PTQ、逐层分析、混合精度、MNN；无赛道mAP，未达2倍。'],
      ['M6-3','CUDA待完成','CPU单参数和1000帧已测；尾延迟未达标，完整GPU Graph未验。'],
      ['M6-4','倍率待优化','三方案各180秒、内部0丢帧；约1.04倍，未达1.6倍。']]
    story.append(table(rows,[48,80,width-128],True)); story+=[Spacer(1,9),p('口径：M3为真实Gazebo物理仿真；M5的导航/抓取演示使用明确Mock；M6为VM CPU结果，不是K230 KPU或Orin成绩。完整录音与室内图片留在本地。','small')]
    story.append(p('界面复查待补：最终浏览器重载被自动审批服务连接故障拒绝，未执行页面操作；HTTP/ROS联测已通过。本次没有最终界面截图。','small'))
    story.append(PageBreak()); story+=[p('实测结果与证据','title'),p('原始CSV、配置、报告和失败记录均随交付保留。','small'),p('动态障碍：三组各10次','heading')]
    nav=[['配置','成功率','成功耗时(s)','规划绕行(m)','转向变化(rad/m)']]
    for row in data['m3_dynamic']: nav.append([row['planner'],str(row['successes'])+'/10',f"{row['seconds']:.2f}",f"{row['extra_length_m']:.3f}",f"{row['steering_variation_rad_per_m']:.3f}"])
    story.append(table(nav,[75,70,110,110,width-365])); story.append(p('耗时使用仿真时钟；绕行来自匹配无障碍参考的/plan估计，不能当成仿真真值里程。激进配置的失败和目标被占据的失败均保留。','small'))
    resources=data['m5_resources']['resources']; story.append(p('监控与交互资源','heading'))
    story.append(table([['指标','聚合器','监控主机'],['平均CPU（单核口径）',f"{resources['aggregator_cpu']['mean']:.2f}%",f"{resources['host_cpu']['mean']:.2f}%"],['峰值RSS',f"{resources['aggregator_rss_mb']['max']:.1f} MB",f"{resources['host_rss_mb']['max']:.1f} MB"]],[220,(width-220)/2,(width-220)/2]))
    story.append(p('聚合器限制：平均CPU&lt;2%、RSS&lt;50MB；主机限制：平均CPU&lt;5%、RSS&lt;200MB。采样持续至少60秒；注入遥测用于故障测试，进程CPU/RSS来自实际测量。','small'))
    story.append(p('模型与稳定性','heading')); cpu=data['m6_cpu']; live=data['m6_live']; tune=data['m6_tuning']; pipe=data['m6_pipeline']['triple']; mnn=data['m6_mnn']
    facts=[['项目','实际结果'],['FP32 CPU基准',f"{cpu['frames']}帧 / {cpu['seconds']:.2f}秒，{cpu['fps']:.2f} FPS，P95 {cpu['p95_ms']:.2f}ms"],['真实USB相机',f"{live['received_frames']}帧，板端跨度{live['board_span_s']:.2f}秒，正常收到结束标志"],['MNN完整口径',f"{mnn['fps']:.2f} FPS，P95 {mnn['p95_ms']:.2f}ms；VM CPU，非Orin"],['1000帧尾延迟',f"P95 {tune['p95_ms']:.2f} / P99 {tune['p99_ms']:.2f} / 最大 {tune['max_ms']:.2f}ms；未达35/50/80ms"],['三线程180秒',f"{pipe['consumed']}帧，内部0丢帧，RSS波动{pipe['rss_warm_range_mb']:.2f}MB，加速比{data['m6_pipeline_speedup']:.2f}"],['基线包自验','Ubuntu 3.10与Windows 3.11独立环境均PASS；均未安装torch/tensorflow。']]
    story.append(table(facts,[112,width-112])); story+=[Spacer(1,8),p('SLAM证据：265个节点、281条边，17条跨历史非邻接约束。真实录音回放验证“小车开始/暂停/停车”；回放与真人直播的记录分别保存。','small')]
    story.append(PageBreak()); story+=[p('待补项与使用入口','title'),p('下列事项不会由电脑成绩或模拟数据代替。','small')]
    for title,text in [
      ('P0 - Orin到货后的板端基准','记录JetPack/驱动/运行时与实际Execution Provider；先做纯推理环境自验，再按CPU/GPU及支持的专用后端连续60秒实测。'),
      ('P0 - 独立赛道数据','提供自有训练权重、独立标注测试集和100～500张不同路段/光照的独立校准图；补逐类mAP、量化掉点与达标判断。当前120张室内相邻帧仅用于功能验证。'),
      ('P1 - CUDA Graph与尾延迟','在真实CUDA硬件上实现、验证完整预处理/推理/后处理链；固定shape和地址，检查节点分区，排除首次捕获，再做1000帧对照。当前只有模型体捕获入口。'),
      ('P1 - 性能达标','INT8至少2倍、mAP下降小于2%；流水线至少1.6倍并满足尾延迟。当前CPU约1.45倍/1.04倍，不能提前标为通过。'),
      ('P2 - 接入实车时的验证','如接真实底盘或机械臂，补硬件急停、标定、真实导航/抓取；现有Mock只验证软件契约。')]: story+=[p(title,'heading'),p(text)]
    story+=[p('Ubuntu启动','heading'),Preformatted('cd ~/smartcar-advanced\nsource scripts/env.sh\nSMARTCAR_SOFTWARE_DEMO=1 bash scripts/start_terminal.sh',styles['code']),Spacer(1,12),p('源码与证据','heading'),p('入口：README_ADVANCED.md；各模块README给出独立复现命令。原始图音、录像和rosbag在本地交付包/Ubuntu保留；Git提供源码、配置及可公开统计。')]
    url='https://github.com/hello1235s/smartcar-m0/tree/codex/m1-m3-m5-m6'
    story.append(p('<link href="'+url+'" color="#0c807d">GitHub：hello1235s/smartcar-m0 · codex/m1-m3-m5-m6</link>'))
    story.append(p('报告依据提交：'+data['git_commit'],'small'))
    def footer(canvas,doc):
        canvas.setFont('SC',8); canvas.setFillColor(muted); canvas.drawString(40,23,'Smartcar training | 实测验收与待补清单'); canvas.drawRightString(A4[0]-40,23,str(doc.page))
    doc=SimpleDocTemplate(str(dest),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=35,bottomMargin=42,title='智能车训练验收状态与待补清单',author='张驰')
    doc.build(story,onFirstPage=footer,onLaterPages=footer); print(dest)


if __name__=='__main__': main()
