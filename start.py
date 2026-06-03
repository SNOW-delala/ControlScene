import json
import uuid
import pyvista as pv
from pyvistaqt import QtInteractor
from deep_translator import GoogleTranslator  # 新增翻译库
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox, QFileDialog, QGroupBox, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt

class SceneEditor3D(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.actors = {}  
        self.label_actor = None  
        self.selected_name = None
        
        # 翻译器与本地缓存（防止重复请求 API 导致卡顿）
        self.translator = GoogleTranslator(source='zh-CN', target='en')
        self.trans_cache = {
            "床": "Bed",
            "桌子": "Desk",
            "洗手台": "Sink",
            "马桶": "Toilet",
            "淋浴间": "Shower"
        }
        
        self.category_colors = {
            "床": "dodgerblue",
            "桌子": "mediumseagreen",
            "洗手台": "cadetblue",
            "马桶": "silver",
            "淋浴间": "skyblue",
            "通用箱体": "tan"
        }
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('ControlScene 室内家具编辑器 (智能翻译版)')
        self.setGeometry(100, 100, 1400, 900)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- 左侧：3D 可视化区域 ---
        self.plotter = QtInteractor(self)
        main_layout.addWidget(self.plotter, stretch=7)
        self.plotter.add_axes()
        
        floor = pv.Plane(center=(2.5, 2.5, 0), direction=(0, 0, 1), i_size=5, j_size=5)
        self.plotter.add_mesh(floor, color="gray", opacity=0.3, show_edges=True, name="room_floor", pickable=False)
        self.plotter.show_grid()
        self.plotter.enable_mesh_picking(callback=self.on_pick, show_message=False, left_clicking=True)

        # --- 右侧：侧边栏控制面板 ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(400)
        sidebar_layout = QVBoxLayout(self.sidebar)
        main_layout.addWidget(self.sidebar, stretch=3)

        file_group = QGroupBox("文件操作")
        file_layout = QHBoxLayout()
        btn_load = QPushButton("导入 JSON")
        btn_load.clicked.connect(self.load_json)
        btn_save = QPushButton("导出 JSON")
        btn_save.clicked.connect(self.export_json)
        file_layout.addWidget(btn_load)
        file_layout.addWidget(btn_save)
        file_group.setLayout(file_layout)
        sidebar_layout.addWidget(file_group)

        # 【新增】视角复位按钮
        btn_reset_view = QPushButton("复位视角 (正面看)")
        btn_reset_view.setStyleSheet("font-weight: bold; height: 35px; background-color: #e1f5fe;")
        btn_reset_view.clicked.connect(self.reset_view)

        edit_group = QGroupBox("对象管理")
        edit_layout = QVBoxLayout()
        add_layout = QHBoxLayout()
        self.combo_add = QComboBox()
        self.combo_add.addItems(["床", "桌子", "洗手台", "马桶", "淋浴间", "通用箱体"])
        btn_add = QPushButton("添加家具")
        btn_add.clicked.connect(self.add_furniture)
        add_layout.addWidget(self.combo_add)
        add_layout.addWidget(btn_add)
        btn_delete = QPushButton("删除选中家具")
        btn_delete.setStyleSheet("background-color: #ffcccc; color: #cc0000;")
        btn_delete.clicked.connect(self.delete_furniture)
        edit_layout.addLayout(add_layout)
        edit_layout.addWidget(btn_delete)
        edit_group.setLayout(edit_layout)
        sidebar_layout.addWidget(edit_group)

        self.prop_group = QGroupBox("属性编辑 (选中家具后生效)")
        self.prop_layout = QFormLayout()
        
        self.input_name = QLineEdit()
        self.input_name.setReadOnly(True) 
        self.input_cat = QLineEdit()
        self.input_pos = QLineEdit() 
        self.input_rot = QLineEdit()
        self.input_size = QLineEdit() 
        self.input_mat = QLineEdit()

        self.prop_layout.addRow("对象 ID:", self.input_name)
        self.prop_layout.addRow("家具类别:", self.input_cat)
        self.prop_layout.addRow("中心坐标 (x,y,z):", self.input_pos)
        self.prop_layout.addRow("旋转角度 (deg):", self.input_rot)
        self.prop_layout.addRow("尺寸 (长,宽,高):", self.input_size)
        self.prop_layout.addRow("材质描述:", self.input_mat)

        btn_apply = QPushButton("应用属性修改")
        btn_apply.clicked.connect(self.apply_manual_edits)
        self.prop_layout.addRow(btn_apply)
        self.prop_group.setLayout(self.prop_layout)
        sidebar_layout.addWidget(self.prop_group)
        sidebar_layout.addStretch()

        tip_label = QLabel("操作提示：\n导入的中文家具名称会自动在后台翻译为英文，确保 3D 标签渲染清晰。导出 JSON 时将保留这些信息。")
        tip_label.setStyleSheet("color: #666; font-size: 12px;")
        tip_label.setWordWrap(True)
        sidebar_layout.addWidget(tip_label)

    # ================= 核心新增：翻译方法 =================
    def get_english_label(self, zh_text):
        """获取中文的英文翻译，自带缓存机制"""
        if not zh_text: return "Object"
        
        # 1. 如果缓存里有，直接返回（极速）
        if zh_text in self.trans_cache:
            return self.trans_cache[zh_text]
            
        # 2. 如果缓存没有，调用网络翻译，并存入缓存
        try:
            en_text = self.translator.translate(zh_text)
            # 简单清洗一下，比如首字母大写
            en_text = en_text.title() if en_text else "Object"
            self.trans_cache[zh_text] = en_text
            return en_text
        except Exception as e:
            print(f"翻译 '{zh_text}' 时出错: {e}")
            return "Object"

    def process_data_translations(self):
        """遍历并预先翻译所有家具的类别"""
        for name, info in self.data.items():
            cat = info.get('category', '')
            if cat and 'en_category' not in info:
                info['en_category'] = self.get_english_label(cat)

    # ====================================================

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择场景 JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                # 导入数据后，立刻进行批量翻译与存储
                self.process_data_translations()
                
                self.selected_name = None
                self.clear_sidebar()
                self.refresh_3d_view()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"读取文件失败: {str(e)}")

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出场景 JSON", "modified_scene.json", "JSON Files (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "成功", "场景已成功导出！")

    def add_furniture(self):
        new_id = "item_" + str(uuid.uuid4())[:6]
        category = self.combo_add.currentText()
        
        dims = [1.0, 1.0, 1.0]
        if category == "床": dims = [2.0, 1.5, 0.5]
        elif category == "桌子": dims = [1.2, 0.6, 0.75]
        elif category == "马桶": dims = [0.7, 0.5, 0.4]
        elif category == "洗手台": dims = [1.0, 0.5, 0.8]
        elif category == "淋浴间": dims = [1.0, 1.0, 2.0]

        self.data[new_id] = {
            "category": category,
            "en_category": self.get_english_label(category), # 添加时直接翻译并存储
            "middle-point": [2.5, 2.5, dims[2]/2], 
            "rotate": 0.0,
            "length": {"value": dims[0], "unit": "m"},
            "width": {"value": dims[1], "unit": "m"},
            "height": {"value": dims[2], "unit": "m"},
            "material": "default"
        }
        
        self.selected_name = new_id
        self.refresh_3d_view()
        self.update_sidebar()

    def delete_furniture(self):
        if not self.selected_name: return
        if self.selected_name in self.data:
            del self.data[self.selected_name]
        self.selected_name = None
        self.clear_sidebar()
        self.refresh_3d_view()

    def refresh_3d_view(self):
        camera_pos = self.plotter.camera_position
        
        for name, actor in self.actors.items():
            self.plotter.remove_actor(actor)
        self.actors = {}
        
        if self.label_actor:
            self.plotter.remove_actor(self.label_actor)
            self.label_actor = None
            
        label_points = []
        label_texts = []
        
        for name, info in self.data.items():
            pos = info['middle-point']
            l = info['length']['value'] if isinstance(info['length'], dict) else info['length']
            w = info['width']['value'] if isinstance(info['width'], dict) else info['width']
            h = info['height']['value'] if isinstance(info['height'], dict) else info['height']
            
            mesh = pv.Box(bounds=(pos[0]-l/2, pos[0]+l/2, pos[1]-w/2, pos[1]+w/2, pos[2]-h/2, pos[2]+h/2))
            
            # 【修复点 1】指定 point=pos，让家具绕着“自己的中心点”自转，而不是绕着房间角落公转
            mesh.rotate_z(info['rotate'], point=pos, inplace=True)
            
            color = "red" if name == self.selected_name else self.category_colors.get(info['category'], "lightgray")
            self.actors[name] = self.plotter.add_mesh(mesh, color=color, opacity=0.8, show_edges=True, name=name)
            
            # 【修复点 2】不再使用手算坐标，而是直接读取 mesh 变换后的真实物理中心和最高点
            actual_center = mesh.center          # 获取网格最终的 (X_center, Y_center, Z_center)
            z_max = mesh.bounds[5]               # bounds 格式为 (xmin, xmax, ymin, ymax, zmin, zmax)，索引 5 就是最高点
            
            # 将标签放置在物体的绝对中心上方 0.15 米处
            label_points.append([actual_center[0], actual_center[1], z_max + 0.15])
            label_texts.append(info.get('en_category', 'Object'))
            
        if label_points:
            self.label_actor = self.plotter.add_point_labels(
                label_points, label_texts, 
                font_size=20,          
                text_color='black',    
                show_points=False,     
                always_visible=True,   
                render_points_as_spheres=False,
                margin=0               
            )
            
        if camera_pos:
            self.plotter.camera_position = camera_pos
        else:
            self.plotter.reset_camera()

    def on_pick(self, mesh):
        if mesh is None:
            if self.selected_name is not None:
                self.selected_name = None
                self.clear_sidebar()
                self.refresh_3d_view() 
            return

        clicked_name = None
        for name, actor in self.actors.items():
            if actor.mapper.dataset == mesh:
                clicked_name = name
                break
                
        if clicked_name and self.selected_name != clicked_name:
            self.selected_name = clicked_name
            self.update_sidebar()
            self.refresh_3d_view() 

    def update_sidebar(self):
        if not self.selected_name: return
        info = self.data[self.selected_name]
        
        self.input_name.setText(self.selected_name)
        self.input_cat.setText(info.get('category', ''))
        self.input_pos.setText(f"{info['middle-point'][0]}, {info['middle-point'][1]}, {info['middle-point'][2]}")
        self.input_rot.setText(str(info['rotate']))
        
        l = info['length']['value'] if isinstance(info['length'], dict) else info['length']
        w = info['width']['value'] if isinstance(info['width'], dict) else info['width']
        h = info['height']['value'] if isinstance(info['height'], dict) else info['height']
        self.input_size.setText(f"{l}, {w}, {h}")
        self.input_mat.setText(info.get('material', ''))

    def clear_sidebar(self):
        self.input_name.clear()
        self.input_cat.clear()
        self.input_pos.clear()
        self.input_rot.clear()
        self.input_size.clear()
        self.input_mat.clear()

    # ================= 核心新增：复位功能 =================
    def reset_view(self):
        """重置相机视角为正面视图"""
        # 定义正面视角：相机位于 Y 轴负方向，看向房间中心 (2.5, 2.5, 0)
        # 格式为：[相机位置, 焦点位置, 向上向量]
        # 我们把相机放在 Y=-5, Z=2.5 的位置，从斜上方正面看入
        front_position = [2.5, -6.0, 3.0] 
        focal_point = [2.5, 2.5, 0.5]
        view_up = [0, 0, 1]
        
        self.plotter.camera_position = [front_position, focal_point, view_up]
        self.plotter.render()

    # ====================================================
    def apply_manual_edits(self):
        if not self.selected_name: return
        try:
            info = self.data[self.selected_name]
            
            # 获取用户输入的新类别
            new_cat = self.input_cat.text()
            
            # 如果类别被修改了，重新触发翻译并存储
            if new_cat != info.get('category', ''):
                info['category'] = new_cat
                info['en_category'] = self.get_english_label(new_cat)
                
            info['middle-point'] = [float(x) for x in self.input_pos.text().split(',')]
            info['rotate'] = float(self.input_rot.text())
            
            dims = [float(x) for x in self.input_size.text().split(',')]
            if isinstance(info['length'], dict):
                info['length']['value'], info['width']['value'], info['height']['value'] = dims
            else:
                info['length'], info['width'], info['height'] = dims
            
            info['material'] = self.input_mat.text()
            self.refresh_3d_view()
        except Exception as e:
            QMessageBox.warning(self, "格式错误", f"请输入正确的格式: {e}")

if __name__ == "__main__":
    app = QApplication([])
    window = SceneEditor3D()
    window.show()
    app.exec_()