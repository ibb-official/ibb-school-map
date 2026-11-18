import { CameraTourStop } from "./types";

export const CAMERA_TOURS: CameraTourStop[] = [
  // WEST CAMPUS TOURS
  {
    id: "tour-w-overview",
    campusId: "west",
    title: "全局鸟瞰",
    subtitle: "东南高位总览西校区南门、连体教学楼与北区操场食堂",
    cameraPos: [48, 70, 44],
    cameraTarget: [-38, 6, -74],
  },
  {
    id: "tour-w-gate",
    campusId: "west",
    title: "南正门·A座",
    subtitle: "同福夹道3号门古铜门额、左侧保安厅门窗与 A 座弧角",
    lightingSuggestion: "sunset",
    cameraPos: [4.5, 8.2, 20.5],
    cameraTarget: [-3.2, 3.0, -7.5],
    highlightPlaceId: "W-G1",
  },
  {
    id: "tour-w-ramp",
    campusId: "west",
    title: "坡道·B座绿地",
    subtitle: "弧形大坡道、雪松庭院、冰心像与入校中轴慎独石",
    lightingSuggestion: "noon",
    cameraPos: [6.0, 12.0, -28.0],
    cameraTarget: [-24.0, 5.0, -52.0],
    highlightPlaceId: "W-R1",
  },
  {
    id: "tour-w-stage",
    campusId: "west",
    title: "主席台·假山水池",
    subtitle: "张拉膜主席台、靠东假山叠水池、左2右3乒乓球台与食堂北侧小门",
    lightingSuggestion: "morning",
    cameraPos: [-23.5, 6.8, -106.5],
    cameraTarget: [-19.5, 2.4, -131.5],
  },
  {
    id: "tour-w-halld",
    campusId: "west",
    title: "校史馆·C座浮雕",
    subtitle: "双层青砖外廊校史馆（D座）、C座五层白色浮雕墙与圆拱顶西邻楼",
    lightingSuggestion: "sunset",
    cameraPos: [-48.0, 14.5, -104.0],
    cameraTarget: [-79.5, 9.5, -86.0],
  },
  {
    id: "tour-w-h1-alley",
    campusId: "west",
    title: "校史馆北穿树门厅",
    subtitle: "人视步入校史馆北侧内巷：高二平房南向通廊、青砖门洞、白卵石穿顶古树与玻璃门厅",
    lightingSuggestion: "morning",
    cameraPos: [-68.2, 1.75, -134.35],
    cameraTarget: [-77.0, 1.85, -134.45],
  },

  // EAST CAMPUS TOURS
  {
    id: "tour-e-overview",
    campusId: "east",
    title: "北巷与南院",
    subtitle: "从东四六条门楼到南院球场的整体关系",
    cameraPos: [52, 58, 46],
    cameraTarget: [-4, 3, -28],
  },
  {
    id: "tour-e-gate",
    campusId: "east",
    title: "东四六条甲44号北门",
    subtitle: "深红门楼、深灰 LED 屏、折叠门与不锈钢校牌",
    lightingSuggestion: "morning",
    cameraPos: [-6.5, 5.4, -101.0],
    cameraTarget: [-6.5, 3.0, -80.5],
    highlightPlaceId: "E-G1",
  },
  {
    id: "tour-e-avenue",
    campusId: "east",
    title: "北巷红砖道",
    subtitle: "6 m 宽、56 m 长的入口巷道与两侧院墙平房",
    lightingSuggestion: "noon",
    cameraPos: [-6.4, 4.2, -76.5],
    cameraTarget: [-6.4, 1.6, -28.0],
    highlightPlaceId: "E-N1",
  },
  {
    id: "tour-e-southyard",
    campusId: "east",
    title: "南院双场",
    subtitle: "两片 13.6 × 25 m 球场与四栋教学楼",
    lightingSuggestion: "sunset",
    cameraPos: [34.0, 26.0, 26.0],
    cameraTarget: [4.0, 3.0, -4.0],
    highlightPlaceId: "E-P1",
  },
];

export function getToursByCampus(campusId: CameraTourStop["campusId"]): CameraTourStop[] {
  return CAMERA_TOURS.filter((t) => t.campusId === campusId);
}
