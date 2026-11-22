"use client";

import { Button, ButtonGroup, Content, Dialog, DialogContainer, Footer, Heading } from "@react-spectrum/s2/Dialog";
import { Divider } from "@react-spectrum/s2/Divider";

interface HelpDialogProps {
  open: boolean;
  onClose: () => void;
}

export function HelpDialog({ open, onClose }: HelpDialogProps) {
  return (
    <DialogContainer onDismiss={onClose}>
      {open && (
        <Dialog isDismissible size="M">
          <Heading slot="title">三维校园地图 · 操控说明</Heading>
          <Content>
            <div className="help-dialog-grid">
              <section className="help-block">
                <h3>键盘自由漫游（桌面端）</h3>
                <ul className="help-kbd-list">
                  <li>
                    <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd>
                    <span>沿当前镜头朝向前后左右平滑漫游（兼容方向键）</span>
                  </li>
                  <li>
                    <kbd>Space</kbd>
                    <span>垂直抬升视角高度</span>
                  </li>
                  <li>
                    <kbd>Shift</kbd>
                    <span>垂直降低视角高度（自动防穿地）</span>
                  </li>
                </ul>
              </section>

              <Divider size="S" />

              <section className="help-block">
                <h3>鼠标操作</h3>
                <p>
                  左键拖拽平移地图，右键拖拽旋转与俯仰视角，滚轮缩放远近；点击校园建筑物或悬浮标签可查看详情与实拍照片。
                </p>
              </section>

              <Divider size="S" />

              <section className="help-block">
                <h3>触屏手势与虚拟按键</h3>
                <p>
                  单指拖动平移地图，双指捏合缩放与双指旋转视角。您也可以在右上角「画质与操控设置」中随时开启<strong>虚拟触屏按键</strong>（电脑端与移动端均可使用），开启后左下角提供平面摇杆、右下角提供上升/下降按钮。
                </p>
              </section>
            </div>
          </Content>
          <Footer>
            <ButtonGroup>
              <Button variant="accent" onPress={onClose}>
                知道了
              </Button>
            </ButtonGroup>
          </Footer>
        </Dialog>
      )}
    </DialogContainer>
  );
}
