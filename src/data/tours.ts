import { CameraTourStop } from "./types";

export const CAMERA_TOURS: CameraTourStop[] = [
  // WEST CAMPUS TOURS
  {
    id: "tour-w-overview",
    campusId: "west",
    title: "全局鸟瞰",
    subtitle: "东南高位总览西校区同福夹道整体体量",
    cameraPos: [54, 68, 48],
    cameraTarget: [-36, 5, -68],
  },
  {
    id: "tour-w-gate",
    campusId: "west",
    title: "南门·慎独石",
    subtitle: "同福夹道3号门古铜门额与慎独校训石",
    lightingSuggestion: "sunset",
    cameraPos: [5.5, 8.5, 22.0],
    cameraTarget: [-3.5, 3.2, -10.0],
    highlightPlaceId: "W-G1",
  },
  {
    id: "tour-w-ramp",
    campusId: "west",
    title: "弧形坡道·B座",
    subtitle: "白边红花箱弧形大坡道与雪松庭院",
    lightingSuggestion: "noon",
    cameraPos: [10.0, 12.5, -34.0],
    cameraTarget: [-21.0, 4.5, -55.0],
    highlightPlaceId: "W-R1",
  },
  {
    id: "tour-w-stage",
    campusId: "west",
    title: "北区操场·主席台",
    subtitle: "三跨弧顶张拉膜、校训双柱与三联篮球场",
    lightingSuggestion: "morning",
    cameraPos: [-62.0, 20.0, -96.0],
    cameraTarget: [-12.0, 5.0, -108.0],
    highlightPlaceId: "W-P2",
  },
  {
    id: "tour-w-halld",
    campusId: "west",
    title: "D座·百草园",
    subtitle: "二层绿栏外廊青砖硬山楼与校园西翼天窗阵",
    lightingSuggestion: "morning",
    cameraPos: [-22.0, 14.0, -102.0],
    cameraTarget: [-40.0, 5.5, -137.0],
    highlightPlaceId: "W-B5",
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
