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
      "同福夹道南正门 2020/2024 立面、东四六条甲44号北正门、自楼梯间二层引出的弧形大坡道、外挂折返楼梯塔、B座南侧绿地慎独石与冰心像、操场北侧张拉膜主席台",
    licenseOrNote: "照片来自公开新闻与学校公开影像，版权归原权利人。",
    url: "https://bj166zx.cn",
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
