import { DataSourceEntry } from "./types";

export const DATA_SOURCES: DataSourceEntry[] = [
  {
    id: "src-osm",
    category: "公开地理矢量底图",
    name: "OpenStreetMap（Overpass API 东城区片区实测轮廓）",
    coverage:
      "西校区边界（way 352521262）、主教学综合楼（way 398697589）、南弧面楼（way 636389217）、东校区南院（way 398694728）、南主及配楼（ways 477977120–477977123）、双联篮球场（838569683–838569684）",
    licenseOrNote: "ODbL 开放数据库许可 · 已转换为 ENU 局部米制工程坐标",
    url: "https://www.openstreetmap.org/",
  },
  {
    id: "src-esri",
    category: "高分辨率正射影像参考",
    name: "Esri World Imagery（Zoom-19 航拍正射瓦片对照校验）",
    coverage:
      "建筑层高与屋面校准（C座 5×8 白色混凝土矩形梁格与阴影高度比、坐北朝南白色弧顶主席台、北侧单层高二平房、西北二层校史馆、东侧圆拱顶食堂及东校区绿屋顶）",
    licenseOrNote: "用于本地三维比例与屋顶平面形态校核；原始影像版权归 Esri 及数据提供方。",
  },
  {
    id: "src-bj166site",
    category: "公开校园实景照片参照",
    name: "bj166-school-site（ibb-official 公开静态图文存档）",
    coverage:
      "同福夹道南正门 2020/2024 立面、自楼梯间二层引出的弧形大坡道、外挂折返楼梯塔、B座南侧绿地慎独石与冰心像、操场北侧张拉膜主席台；东校区北门仅作年代对照",
    licenseOrNote: "照片来自公开新闻与学校公开影像，版权归原权利人。",
    url: "https://bj166zx.cn",
  },
  {
    id: "src-wikimedia-east-gate",
    category: "公开校园实景照片",
    name: "Wikimedia Commons：北京市第一六六中学北校区大门（2023-11-11）",
    coverage:
      "东四六条甲44号北门立面细部：门柱尺度、深灰 LED 屏、折叠门、不锈钢校牌、地址牌、竖牌、门房与限速 5 标线；东校区入口区几何校正的主要依据",
    licenseOrNote: "摄影 N509FZ，CC BY-SA 4.0；已按许可署名，未做裁剪以外的改动",
    url: "https://commons.wikimedia.org/wiki/File:Beijing_No._166_Middle_School,_north_campus_(20231111164512).jpg",
  },
  {
    id: "src-amap",
    category: "高分辨率正射影像参考",
    name: "高德地图卫星影像（z18，GCJ-02 反算配准）",
    coverage:
      "东校区校园边界复核、北巷宽度与两侧院墙、球场尺寸与缓冲区、B5 绿顶体量、西侧蓝色屋面、南院北缘裸土区；与 Esri 影像交叉校验",
    licenseOrNote: "仅用于本地几何校核，原始影像版权归高德及数据提供方。",
    url: "https://www.amap.com/",
  },
  {
    id: "src-bjnews",
    category: "公开媒体报道资料",
    name: "新京报公开校园建设及160周年校庆新闻报道",
    coverage:
      "西校区室外弧形坡道（雪松与红色花箱）、B/C/D座红色书本牌匾、校园百草园开敞花园、无车棚自行车停放区与音乐长廊空间功能校核",
    licenseOrNote: "用于校园公共空间与建筑细节对照。",
  },
];
