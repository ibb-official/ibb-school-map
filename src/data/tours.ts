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
    subtitle: "弧形大坡道、雪松庭院与冰心像/慎独石前 B 座立面",
    lightingSuggestion: "noon",
    cameraPos: [6.0, 12.0, -28.0],
    cameraTarget: [-24.0, 5.0, -52.0],
    highlightPlaceId: "W-R1",
  },
  {
    id: "tour-w-stage",
    campusId: "west",
    title: "主席台·高二平房",
    subtitle: "坐北朝南张拉膜主席台、左侧国旗杆与两侧音响、后方高二平房",
    lightingSuggestion: "morning",
    cameraPos: [-45.5, 13.0, -90.0],
    cameraTarget: [-45.5, 4.5, -129.0],
    highlightPlaceId: "W-P2",
  },
  {
    id: "tour-w-halld",
    campusId: "west",
    title: "校史馆·C座连体楼",
    subtitle: "西北角2层校史馆（D座）与屋顶白色梁格 6 层 C 座",
    lightingSuggestion: "morning",
    cameraPos: [-56.0, 22.0, -92.0],
    cameraTarget: [-75.0, 7.0, -108.0],
    highlightPlaceId: "W-H1",
  },

  // EAST CAMPUS TOURS
  {
    id: "tour-e-overview",
    campusId: "east",
    title: "双院鸟瞰",
    subtitle: "北合院落与南教学楼群全景关系",
    cameraPos: [62, 64, 54],
    cameraTarget: [8, 4, -20],
  },
  {
    id: "tour-e-gate",
    campusId: "east",
    title: "东四六条北门",
    subtitle: "朱红门额灰瓦挑檐、左青砖门房与限速5标志",
    lightingSuggestion: "morning",
    cameraPos: [-3.5, 7.2, -104.0],
    cameraTarget: [-2.0, 3.0, -80.5],
    highlightPlaceId: "E-G1",
  },
  {
    id: "tour-e-avenue",
    campusId: "east",
    title: "55m林荫红砖道",
    subtitle: "纵贯北四合院东西厢房的林荫红砖轴线",
    lightingSuggestion: "noon",
    cameraPos: [-3.0, 9.5, -90.0],
    cameraTarget: [-3.0, 2.5, -35.0],
    highlightPlaceId: "E-N1",
  },
  {
    id: "tour-e-southyard",
    campusId: "east",
    title: "南院双场与绿顶楼",
    subtitle: "双联标准篮球场与四座南院教学建筑群",
    lightingSuggestion: "sunset",
    cameraPos: [34.0, 28.0, 28.0],
    cameraTarget: [6.0, 4.0, -8.0],
    highlightPlaceId: "E-P1",
  },
];

export function getToursByCampus(campusId: CameraTourStop["campusId"]): CameraTourStop[] {
  return CAMERA_TOURS.filter((t) => t.campusId === campusId);
}
