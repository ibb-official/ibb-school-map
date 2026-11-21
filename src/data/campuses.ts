import { CampusId, CampusMeta } from "./types";

export const CAMPUSES: Record<CampusId, CampusMeta> = {
  west: {
    id: "west",
    name: "西校区 · 同福夹道校本部",
    shortName: "西校区",
    roleLabel: "校本部 / 初中及综合校园",
    address: "北京市东城区同福夹道3号",
    district: "东城区 · 灯市口—东四南片区",
    modelUrl: "/models/west-campus.glb?v=afa3c026",
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
      "西校区保留了老北京胡同文脉与立体教学连廊空间格局：南正门直通东侧主通道与 A 座弧角综合楼，中部为 C 座（北立面嵌五层白色主题浮雕）、90°北凸楼梯间枢纽、B 座（150°钝角折弯东北斜翼）连体 6 层核心教学楼群；入校中轴布置慎独石，南侧绿地布置冰心像与自二层引出的弧形大坡道及老雪松，西合百草园（含亭子、月季与青松/银杏/柿树/玉兰）与音乐长廊，北部展开西贴围墙的紧凑型环形塑胶操场（四周跑道与四角同铺颗粒塑胶、中心椭圆偏硬球场地坪容三片篮球场与南侧露天自行车停放区）、深灰石材台基张拉膜主席台、靠东设假山叠水池及左2右3共5张乒乓球台的高二平房区、西北角双层青砖外廊校史馆（D 座，北设穿树半露天庭院入口），以及东侧圆拱顶学生食堂与北连青砖硬山附属校舍（带向校内开放小门）。",
  },
  east: {
    id: "east",
    name: "东校区 · 东四六条甲44号",
    shortName: "东校区",
    roleLabel: "高三毕业年级部（原北京市第128中学）",
    address: "北京市东城区东四六条甲44号",
    district: "东城区 · 东四历史文化保护街区",
    modelUrl: "/models/east-campus.glb?v=f9c2fa7e",
    approxAreaSqm: "约 6,200 m²（南院 5,769 m² + 北向入口巷约 340 m² + 门前约 120 m²）",
    defaultCameraPos: [46, 50, 38],
    defaultCameraTarget: [-4, 3, -18],
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
      "东校区是倒 T 形格局：南院集中四栋教学楼、两片 13.6 × 25 m 球场与活动场地，场边有链式围网和四角灯杆；北侧经东四六条甲44号的深红门楼进入一条约 6 m 宽、56 m 长的红砖巷道，两侧紧贴院墙与平房（西侧有一栋带檐廊的单层房，东侧为树院），尽头接运动区。",
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
