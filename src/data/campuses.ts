import { CampusId, CampusMeta } from "./types";

export const CAMPUSES: Record<CampusId, CampusMeta> = {
  west: {
    id: "west",
    name: "西校区 · 同福夹道校本部",
    shortName: "西校区",
    roleLabel: "校本部 / 初中及综合校园",
    address: "北京市东城区同福夹道3号",
    district: "东城区 · 灯市口—东四南片区",
    modelUrl: "/models/west-campus.glb?v=7fbb58f1",
    approxAreaSqm: "约 13,500 m²（南北纵深约 137 m × 东西宽约 101 m）",
    defaultCameraPos: [48, 70, 44],
    defaultCameraTarget: [-38, 6, -74],
    panBounds: {
      minX: -145,
      maxX: 60,
      minZ: -175,
      maxZ: 55,
    },
    nearestTransit: [
      "地铁5号线「灯市口站」A/C口（步行约420 m）",
      "地铁8号线「金鱼胡同站」东北口（步行约560 m）",
      "公交「灯市西口」「米市大街」站",
    ],
    surroundingStreets: [
      "同福夹道（南侧正门通道）",
      "丰富胡同 / 灯市口北巷",
      "灯市口小学周边街区（西邻）",
    ],
    summary:
      "西校区保留了老北京胡同文脉与立体教学连廊空间格局：南正门直通东侧主通道与 A 座弧角综合楼，中部为 C 座（北立面嵌五层白色主题浮雕）、90°北凸楼梯间枢纽、B 座（150°钝角折弯东北斜翼）连体 6 层核心教学楼群；南侧绿地布置冰心像、慎独石与自二层引出的弧形大坡道及老雪松，西合百草园与音乐长廊，北部展开 200 m 环形塑胶操场（含绿桁架玻璃篮板球架、西墙单杠保护垫与南侧露天自行车停放区）、深灰石材台基张拉膜主席台、带挑廊与太湖石假山乒乓球区的高二平房区（向西延伸至校史馆北侧）、西北角双层青砖外廊校史馆（D 座，北设穿树半露天庭院与玻璃门厅入口）及东侧圆拱顶学生食堂。",
  },
  east: {
    id: "east",
    name: "东校区 · 东四六条甲44号",
    shortName: "东校区",
    roleLabel: "高三毕业年级部（原徐世昌弢园旧址所在片区）",
    address: "北京市东城区东四六条甲44号",
    district: "东城区 · 东四历史文化保护街区",
    modelUrl: "/models/east-campus.glb?v=b95ef1fc",
    approxAreaSqm: "约 8,800 m²（南北呈哑铃式前后两院格局）",
    defaultCameraPos: [62, 64, 54],
    defaultCameraTarget: [8, 4, -20],
    panBounds: {
      minX: -85,
      maxX: 105,
      minZ: -125,
      maxZ: 85,
    },
    nearestTransit: [
      "地铁5号线 / 6号线「东四站」（向北经东四北大街步行约580 m）",
      "地铁5号线「张自忠路站」C/D口（步行约620 m）",
      "公交「东四六条」「钱粮胡同」站",
    ],
    surroundingStreets: [
      "东四六条（北侧朱红筒瓦校门临街面）",
      "东四北大街（西侧主干道）",
      "东四五条 / 东四七条历史四合院保护胡同",
    ],
    summary:
      "东校区呈独特的“北古南新”南北双院落布局：北侧自东四六条甲44号朱红门柱筒瓦门楼步入，沿 55 米红砖林荫甬道两侧分布青砖灰瓦合院平房肌理；南院则汇集四座绿色/灰色屋面教学楼、双联标准篮球场与活动广场。",
  },
};

export const DUAL_CAMPUS_LINK = {
  straightLineKm: 1.24,
  deltaEastMeters: 558,
  deltaNorthMeters: 1112,
  walkingMinutes: "约 18 分钟（1.55 km）",
  cyclingMinutes: "约 7 分钟",
  corridors: [
    "灯市口北巷 → 同福夹道 → 东四南大街 → 东四北大街 → 东四六条",
    "也可经干面胡同—朝阳门北小街一线南北通行",
  ],
  historicalContext:
    "两校区同处东城核心历史风貌保护区（隆福寺—东四片区），相距仅 1.24 公里，形成“同福夹道本部 + 东四六条毕业部”联动格局。",
};
