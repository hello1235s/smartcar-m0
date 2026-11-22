"""Read-only click-to-inspect original projected pixels and recorded LaserScan beams."""
import argparse
import json
from pathlib import Path
import signal
import sys
from PyQt5 import QtCore,QtGui,QtWidgets,QtTest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('points',type=Path)
    parser.add_argument('--verify-click',action='store_true')
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    data=json.loads(args.points.read_text())
    image_path=args.points.parent/data['image']
    app=QtWidgets.QApplication(sys.argv[:1]);window=QtWidgets.QWidget()
    window.setWindowTitle('M1-3 recorded pixel / LaserScan distance inspector')
    layout=QtWidgets.QVBoxLayout(window);heading=QtWidgets.QLabel('Click a projected point; distance comes from original LaserScan.ranges[index].')
    label=QtWidgets.QLabel();pixmap=QtGui.QPixmap(str(image_path));assert not pixmap.isNull()
    label.setPixmap(pixmap);label.setFixedSize(pixmap.size());result=QtWidgets.QLabel('No point selected')
    result.setMinimumHeight(58)
    layout.addWidget(heading);layout.addWidget(label);layout.addWidget(result)
    selected={}
    def click(event):
        if not data['points']:return
        point=min(data['points'],key=lambda p:(p['pixel'][0]-event.x())**2+(p['pixel'][1]-event.y())**2)
        distance=(point['pixel'][0]-event.x())**2+(point['pixel'][1]-event.y())**2
        if distance>49:result.setText('Click within 7 pixels of a recorded point.');return
        selected.update(point)
        result.setText('pixel=(%d,%d)  beam=%d  range=%.6f m\nscan stamp=%d ns | image stamp=%d ns'%(
            *point['pixel'],point['beam_index'],point['distance_m'],data['scan_stamp_ns'],data['image_stamp_ns']))
    label.mousePressEvent=click
    signal.signal(signal.SIGINT,lambda *_:app.quit());signal.signal(signal.SIGTERM,lambda *_:app.quit())
    window.show()
    if args.verify_click:
        assert args.out is not None and data['points']
        def verify():
            # Choose a unique visible pixel so that overlapping points cannot make the expected beam ambiguous.
            counts={tuple(p['pixel']):sum(q['pixel']==p['pixel'] for q in data['points']) for p in data['points']}
            expected=next(p for p in data['points'] if counts[tuple(p['pixel'])]==1)
            QtTest.QTest.mouseClick(label,QtCore.Qt.LeftButton,pos=QtCore.QPoint(*expected['pixel']))
            assert selected==expected
            args.out.mkdir(parents=True,exist_ok=False)
            window.grab().save(str(args.out/'actual_point_inspector.png'))
            (args.out/'click_check.json').write_text(json.dumps(dict(status='PASS',input=str(args.points),
                click=expected['pixel'],selected=selected,label=result.text(),original_image_unmodified=True),indent=2))
            QtCore.QTimer.singleShot(1500,app.quit)
        QtCore.QTimer.singleShot(500,verify)
    app.exec_()

if __name__=='__main__':main()
