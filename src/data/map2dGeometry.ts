/**
 * Exact ENU metric 2D footprints (meters relative to each campus origin)
 * extracted from blender/data/west_metric.json & east_metric.json
 * for the interactive 2D CAD / SVG fallback and overview map.
 */

export type EnuPoint = [number, number];

export interface Map2DPolygon {
  id: string;
  placeId?: string;
  kind:
    | "boundary"
    | "academic"
    | "heritage"
    | "sports"
    | "sports-track"
    | "sports-court"
    | "gate"
    | "corridor"
    | "context"
    | "road";
  label?: string;
  pts: EnuPoint[];
}

export const WEST_2D_POLYGONS: Map2DPolygon[] = [
  {
    id: "west-road-tongfu",
    kind: "road",
    label: "同福夹道",
    pts: [
      [-6, -40],
      [6, -40],
      [6, 8],
      [-6, 8],
    ],
  },
  {
    id: "west-boundary",
    kind: "boundary",
    pts: [
      [-93.45, 129.88],
      [-21.82, 135.12],
      [-14.22, 135.8],
      [-12.12, 134.14],
      [-10.67, 132.24],
      [-6.48, 127.16],
      [-6.18, 121.59],
      [-5.51, 100.11],
      [2.5, 100.08],
      [3.64, 5.13],
      [-2.07, 5.6],
      [-10.88, 5.48],
      [-16.02, 10.92],
      [-22.98, 18.9],
      [-28.66, 23.92],
      [-83.23, 22.25],
      [-93.16, 68.6],
      [-93.19, 75.34],
    ],
  },
  {
    id: "west-neighbor-primary",
    kind: "context",
    label: "西邻小学建筑区",
    pts: [
      [-92.56, 63.56],
      [-91.52, 30.21],
      [-104.71, 29.8],
      [-104.36, 18.58],
      [-170.99, 16.51],
      [-171.42, 30.39],
      [-166.27, 30.56],
      [-167.23, 61.25],
    ],
  },
  {
    id: "w-p1-outer",
    placeId: "W-P1",
    kind: "sports-track",
    label: "W-P1 塑胶操场",
    pts: [
      [-91.5, 89.0],
      [-9.5, 89.0],
      [-9.5, 128.5],
      [-91.5, 128.5],
    ],
  },
  {
    id: "w-p1-inner",
    placeId: "W-P1",
    kind: "sports-court",
    pts: [
      [-82.0, 95.0],
      [-18.0, 95.0],
      [-18.0, 122.0],
      [-82.0, 122.0],
    ],
  },
  {
    id: "w-l2-garden",
    placeId: "W-L2",
    kind: "heritage",
    label: "W-L2 百草园",
    pts: [
      [-64.0, 41.5],
      [-25.0, 41.5],
      [-25.0, 56.0],
      [-64.0, 56.0],
    ],
  },
  {
    id: "w-b1",
    placeId: "W-B1",
    kind: "academic",
    label: "W-B1 西翼 C 座",
    pts: [
      [-90.0, 76.1],
      [-69.8, 77.3],
      [-68.2, 34.3],
      [-79.9, 34.0],
      [-81.0, 49.8],
      [-87.7, 53.5],
    ],
  },
  {
    id: "w-b2",
    placeId: "W-B2",
    kind: "academic",
    label: "W-B2 中北连廊段",
    pts: [
      [-69.8, 77.2],
      [-54.9, 77.1],
      [-55.8, 61.9],
      [-69.3, 61.7],
    ],
  },
  {
    id: "w-b3",
    placeId: "W-B3",
    kind: "academic",
    label: "W-B3 B 座主楼",
    pts: [
      [-47.0, 77.2],
      [-37.5, 68.4],
      [-8.4, 87.4],
      [-2.0, 75.7],
      [-36.3, 57.4],
      [-47.0, 57.6],
    ],
  },
  {
    id: "w-b4",
    placeId: "W-B4",
    kind: "academic",
    label: "W-B4 弧面楼",
    pts: [
      [-27.65, 44.59],
      [-19.17, 42.52],
      [-13.22, 37.72],
      [-10.01, 26.96],
      [-4.97, 26.04],
      [-4.52, 8.18],
      [-10.7, 8.64],
      [-10.7, 14.36],
      [-15.74, 13.45],
      [-15.97, 17.57],
      [-19.63, 17.11],
      [-21.46, 24.67],
      [-30.62, 27.64],
      [-54.9, 27.87],
      [-56.73, 39.79],
      [-28.56, 40.7],
    ],
  },
  {
    id: "w-b5",
    placeId: "W-B5",
    kind: "academic",
    label: "W-B5 D 座楼",
    pts: [
      [-77.0, 132.0],
      [-19.0, 135.0],
      [-19.5, 144.8],
      [-77.5, 141.8],
    ],
  },
  {
    id: "w-b6",
    placeId: "W-B6",
    kind: "academic",
    label: "W-B6 红瓦体美楼",
    pts: [
      [3.8, 37.0],
      [12.6, 37.0],
      [12.6, 95.0],
      [3.8, 95.0],
    ],
  },
  {
    id: "w-mc",
    placeId: "W-MC",
    kind: "corridor",
    label: "W-MC 音乐长廊",
    pts: [
      [-95.4, 58.0],
      [-89.9, 58.0],
      [-89.9, 78.2],
      [-95.4, 78.2],
    ],
  },
  {
    id: "w-r1",
    placeId: "W-R1",
    kind: "corridor",
    label: "W-R1 弧形大坡道",
    pts: [
      [-38.0, 58.2],
      [-26.0, 60.0],
      [-13.0, 58.6],
      [-4.2, 52.0],
      [-5.6, 49.6],
      [-15.0, 55.6],
      [-26.0, 56.4],
      [-38.0, 54.8],
    ],
  },
  {
    id: "w-st1",
    placeId: "W-ST1",
    kind: "corridor",
    label: "W-ST1 楼梯塔",
    pts: [
      [-8.7, 77.9],
      [-2.3, 77.9],
      [-2.3, 85.4],
      [-8.7, 85.4],
    ],
  },
  {
    id: "w-p2",
    placeId: "W-P2",
    kind: "sports",
    label: "W-P2 主席台",
    pts: [
      [-11.5, 97.5],
      [-4.5, 97.5],
      [-4.5, 118.5],
      [-11.5, 118.5],
    ],
  },
  {
    id: "w-g1",
    placeId: "W-G1",
    kind: "gate",
    label: "W-G1 南正门",
    pts: [
      [-11.1, 4.2],
      [5.8, 4.2],
      [5.8, 9.5],
      [-11.1, 9.5],
    ],
  },
  {
    id: "w-l1",
    placeId: "W-L1",
    kind: "heritage",
    label: "W-L1 慎独石",
    pts: [
      [-8.6, 15.0],
      [-4.2, 15.0],
      [-4.2, 20.0],
      [-8.6, 20.0],
    ],
  },
  {
    id: "w-l3",
    placeId: "W-L3",
    kind: "heritage",
    label: "W-L3 校友雕像",
    pts: [
      [-12.6, 19.8],
      [-9.8, 19.8],
      [-9.8, 22.6],
      [-12.6, 22.6],
    ],
  },
];

export const EAST_2D_POLYGONS: Map2DPolygon[] = [
  {
    id: "east-road-liutiao",
    kind: "road",
    label: "东四六条胡同（北门通道）",
    pts: [
      [-45, 81.5],
      [62, 81.5],
      [62, 91.5],
      [-45, 91.5],
    ],
  },
  {
    id: "east-boundary-north",
    kind: "boundary",
    pts: [
      [-35.5, 23.5],
      [54.3, 24.5],
      [54.3, 80.5],
      [-35.5, 80.5],
    ],
  },
  {
    id: "east-boundary-south",
    kind: "boundary",
    pts: [
      [-35.51, 23.53],
      [54.33, 24.91],
      [55.31, -39.28],
      [-34.53, -40.67],
    ],
  },
  {
    id: "e-p1-outer",
    placeId: "E-P1",
    kind: "sports-track",
    label: "E-P1 运动区",
    pts: [
      [-6.0, -16.0],
      [31.0, -15.5],
      [30.5, 19.0],
      [-6.0, 18.5],
    ],
  },
  {
    id: "e-p1-court-w",
    placeId: "E-P1",
    kind: "sports-court",
    pts: [
      [-1.27, 13.05],
      [11.76, 13.34],
      [12.33, -11.33],
      [-0.71, -11.62],
    ],
  },
  {
    id: "e-p1-court-e",
    placeId: "E-P1",
    kind: "sports-court",
    pts: [
      [13.71, 13.47],
      [26.74, 13.77],
      [27.31, -10.9],
      [14.26, -11.2],
    ],
  },
  {
    id: "e-p1-activity",
    placeId: "E-P1",
    kind: "sports-court",
    pts: [
      [-32.0, 4.5],
      [-11.0, 4.8],
      [-11.0, 18.5],
      [-32.0, 18.0],
    ],
  },
  {
    id: "e-n1",
    placeId: "E-N1",
    kind: "corridor",
    label: "E-N1 55m 红砖林荫道",
    pts: [
      [-7.2, 22.0],
      [1.2, 22.0],
      [1.2, 79.0],
      [-7.2, 79.0],
    ],
  },
  {
    id: "e-n2-south",
    placeId: "E-N2",
    kind: "heritage",
    label: "E-N2 北院东厢（南进）",
    pts: [
      [10.0, 42.8],
      [38.0, 42.8],
      [38.0, 53.3],
      [10.0, 53.3],
    ],
  },
  {
    id: "e-n2-north",
    placeId: "E-N2",
    kind: "heritage",
    label: "E-N2 北院东厢（北进）",
    pts: [
      [10.0, 61.2],
      [38.0, 61.2],
      [38.0, 70.7],
      [10.0, 70.7],
    ],
  },
  {
    id: "e-n3",
    placeId: "E-N3",
    kind: "heritage",
    label: "E-N3 北院西厢合院",
    pts: [
      [-29.5, 40.0],
      [-15.5, 40.0],
      [-15.5, 64.0],
      [-29.5, 64.0],
    ],
  },
  {
    id: "e-b1",
    placeId: "E-B1",
    kind: "academic",
    label: "E-B1 南主教学楼",
    pts: [
      [-13.91, -18.33],
      [31.07, -17.43],
      [31.25, -26.19],
      [27.1, -26.28],
      [27.21, -31.65],
      [-9.88, -32.39],
      [-10.0, -26.43],
      [-13.75, -26.51],
    ],
  },
  {
    id: "e-b2",
    placeId: "E-B2",
    kind: "academic",
    label: "E-B2 西南 L 形楼",
    pts: [
      [-32.1, -15.63],
      [-24.43, -15.66],
      [-24.41, -12.32],
      [-21.84, -12.33],
      [-21.85, -15.67],
      [-16.52, -15.7],
      [-16.62, -38.68],
      [-32.2, -38.61],
    ],
  },
  {
    id: "e-b3",
    placeId: "E-B3",
    kind: "academic",
    label: "E-B3 东南配楼",
    pts: [
      [33.46, -17.11],
      [37.04, -17.05],
      [37.08, -19.85],
      [39.99, -19.8],
      [39.96, -17.18],
      [54.28, -16.97],
      [54.48, -30.89],
      [31.41, -31.23],
      [31.36, -27.92],
      [33.63, -27.89],
    ],
  },
  {
    id: "e-b4",
    placeId: "E-B4",
    kind: "academic",
    label: "E-B4 西中教学楼",
    pts: [
      [-32.66, 2.27],
      [-14.74, 2.62],
      [-14.51, -9.17],
      [-32.43, -9.53],
    ],
  },
  {
    id: "e-b5",
    placeId: "E-B5",
    kind: "academic",
    label: "E-B5 东缘坡顶房",
    pts: [
      [37.0, -14.0],
      [49.0, -14.0],
      [49.0, 16.0],
      [37.0, 16.0],
    ],
  },
  {
    id: "e-g1",
    placeId: "E-G1",
    kind: "gate",
    label: "E-G1 东四六条北门",
    pts: [
      [-8.3, 76.0],
      [8.8, 76.0],
      [8.8, 82.0],
      [-8.3, 82.0],
    ],
  },
];
