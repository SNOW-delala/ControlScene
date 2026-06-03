# coding=utf-8
import requests
import json
import re
from pathlib import Path
import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QFileDialog
)
from socket import *
import settings
import base64
import os
import sys

def base64_decode_img(base64_code):
    """
    :param base64_code: base64编码
    :return: 二进制据,直接写入保存为图片
    """
    img_bytes = base64.b64decode(base64_code)
    return img_bytes

def get_chat_response(text, 
                     model="deepseek-chat",
                     api_key=None,
                     stream=True):
    # 安全提示：建议通过环境变量获取API密钥
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("API密钥未提供，请通过环境变量DEEPSEEK_API_KEY设置")

    url = "https://api.deepseek.com/v1/chat/completions"  # 更新为最新API端点
    
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": text
        }],
        "temperature": 0.7,
        "stream": stream
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",  # 修正拼写错误
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    full_content = ""
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=headers, 
            stream=stream,
            timeout=30
        )
        response.raise_for_status()

        for chunk in response.iter_lines():
            if chunk:
                decoded_chunk = chunk.decode('utf-8').strip()
                if decoded_chunk.startswith('data:'):
                    json_str = decoded_chunk[5:].strip()
                    if json_str == "[DONE]":
                        break
                        
                    try:
                        data = json.loads(json_str)
                        if data.get('choices'):
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content') or delta.get('reasoning_content') or ""
                            full_content += content
                            print(content, end='', flush=True)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {str(e)}")
                        continue

        return full_content
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"错误详情: {e.response.text}")
        return None


def parse_css_like_data(css_text, output_file=None):
    """
    增强版解析函数，包含错误处理和结果保存功能
    
    参数：
    css_text : str - 需要解析的CSS格式文本
    output_file : str - (可选) 指定保存结果的JSON文件路径
    
    返回：
    dict - 解析后的结构化数据，同时可选保存到JSON文件
    """
    pattern = r"\.(\w+)\s*{\s*((?:[^}]+?))\s*}"
    items = re.findall(pattern, css_text, re.DOTALL)
    
    result = {}
    
    for name, content in items:
        attributes = {}
        lines = [line.strip() for line in content.split(';') if line.strip()]
        
        for line in lines:
            try:
                key, value = re.split(r"\s*:\s*", line, 1)
                
                # 处理不同数据类型
                if value.startswith("'"):
                    attributes[key] = value.strip("'")
                elif value.startswith("("):
                    attributes[key] = [float(x) for x in re.findall(r"[-+]?\d+\.?\d*", value)]
                elif 'deg' in value:
                    attributes[key] = float(re.search(r"[-+]?\d+\.?\d*", value).group())
                elif any(unit in value for unit in ['m', 'cm', 'mm']):
                    match = re.match(r"^\s*([-+]?\d+\.?\d*)\s*([a-zA-Z]+)\s*$", value)
                    if match:
                        num, unit = match.groups()
                        attributes[key] = {"value": float(num), "unit": unit}
                    else:
                        print(f"警告：无法解析尺寸值 '{value}'，家具 '{name}' 的属性 '{key}'")
                        attributes[key] = value
                else:
                    attributes[key] = value
                    
            except Exception as e:
                print(f"解析错误：家具 '{name}' 行 '{line}' | 错误：{str(e)}")
                continue
                
        result[name] = attributes
    
    # 保存到JSON文件（如果指定了输出路径）
    if output_file:
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, 
                         indent=2, 
                         ensure_ascii=False,
                         default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o))
            
            print(f"成功保存结果到：{output_path.absolute()}")
        except Exception as e:
            print(f"文件保存失败：{str(e)}")
    
    return result

class Client():
    def __init__(self, host=settings.ip_addr, port=settings.port):
        self.host = host
        self.port = port
        self.socket = self.connect()
        self.save_path = './result'

    def connect(self):
        tcp_socket = socket()
        tcp_socket.connect((self.host, self.port))
        return tcp_socket

    def send_msg(self, msg):
        self.socket.send(msg.encode())

    def receive_msg(self, bufsize=1024):
        data_received = self.socket.recv(bufsize).decode()
        return data_received
    
    def close(self):
        self.socket.close()
    
    def recive_img(self,size):
        #size表示传输次数
        name = 'pano_enhance'
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        img_data = "" # 需要存储的图片数据
        m = 0
        # n = 0
        while m < size:
            data = self.socket.recv(1024)  # 直接使用socket接收数据
            # n = n + len(data)
            # print("已经接收数据大小是：",n,";新接收数据大小是：",len(data))
            # print(data)
            img_data += data.decode()  # 累加接收到的数据
            m = m + 1
            
            

        # 确保接收到的数据是完整的base64编码数据
        if img_data:
            d = base64_decode_img(img_data)  # 假设服务器发送的是base64编码的字符串
            with open(f"{self.save_path}/{name}.jpg", "wb") as f:
                f.write(d)
        else:
            print("未接收到有效的图片数据")

class ObjectEditor(QMainWindow):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.current_obj = None
        self.initUI()
        self.setup_3d_view()
        self.update_visualization()
        self.right_click_position = None

    def initUI(self):
        # 主窗口设置
        self.setWindowTitle('3D Object Editor')
        self.setGeometry(100, 100, 1200, 800)
        # 设置整个窗口的样式表
        self.setStyleSheet("""
            QMainWindow {
                font-size: 25px;
                font-family: 'Times New Roman';
                font-weight: bold; 
            }
            QPushButton {
                font-size: 25px;
                font-family: 'Times New Roman';
                font-weight: bold;
            }
            QLabel {
                font-size: 25px;
                font-family: 'Times New Roman';
                font-weight: bold;
            }
            QLineEdit {
                font-size: 25px;
                font-family: 'Times New Roman';
                font-weight: bold;
            }
            QComboBox {
                font-size: 25px;
                font-family: 'Times New Roman';
                font-weight: bold;
            }
        """)

        # 创建主控件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 3D可视化区域（关键修改点1：正确初始化QtInteractor）
        self.plotter = QtInteractor(main_widget)
        layout.addWidget(self.plotter, stretch=5)

        # 控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)

        # 属性编辑组件
        self.lbl_name = QLabel("Choose: None")
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(['Bed', 'Wardone', 'Desk', 'Seat', 'Else'])
        self.txt_material = QLineEdit()
        self.txt_position = QLineEdit()
        self.txt_dimensions = QLineEdit()
        
        control_layout.addWidget(QLabel("Operation:"))
        control_layout.addWidget(self.lbl_name)
        control_layout.addWidget(QLabel("Category:"))
        control_layout.addWidget(self.cmb_category)
        control_layout.addWidget(QLabel("Material:"))
        control_layout.addWidget(self.txt_material)
        control_layout.addWidget(QLabel("Middle-point (x,y,z):"))
        control_layout.addWidget(self.txt_position)
        control_layout.addWidget(QLabel("Size (Length,Width,Height):"))
        control_layout.addWidget(self.txt_dimensions)
        
        # 按钮
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_changes)
        btn_export = QPushButton("Export")
        btn_export.clicked.connect(self.export_data)
        
        control_layout.addWidget(btn_save)
        control_layout.addWidget(btn_export)
        layout.addWidget(control_panel, stretch=2)


    def setup_3d_view(self):
        """初始化3D视图设置（关键修改点2：通过plotter访问PyVista原生接口）"""
        # 启用表面拾取
        self.plotter.enable_surface_point_picking(
            callback=self.select_object, 
            left_clicking=True,
            show_message="点击选择物体"
        )
        self.plotter.add_axes()
        self.plotter.interactor.AddObserver("RightButtonPressEvent", self.on_right_click)
        self.plotter.show_grid()

    def on_right_click(self, obj, event):
        """右键点击事件处理"""
        # 获取点击位置的3D坐标
        click_pos = self.plotter.pick_mouse_position()
        self.right_click_position = np.array(click_pos)
        print("右键点击坐标为：",self.right_click_position)
        
        # 查找包含该点的盒子
        self.find_containing_box()
        
        # 阻止默认的右键旋转行为
        # event.Skip()

    def find_containing_box(self):
        """查找包含当前点的盒子"""
        if self.right_click_position is None:
            return
        
        for obj_name, obj_data in self.data.items():
            print("查找物品",obj_name)
            bounds = self.get_box_bounds(obj_data)
            print("计算出来的边界是：\n")
            print("x对应:",bounds[0],bounds[1])
            print("y对应:",bounds[2],bounds[3])
            print("z对应:",bounds[4],bounds[5])
            
            # 检查坐标是否在边界内
            if (bounds[0] <= self.right_click_position[0] <= bounds[1] and
                bounds[2] <= self.right_click_position[1] <= bounds[3] and
                bounds[4] <= self.right_click_position[2] <= bounds[5]):
                
                self.current_obj = obj_name
                self.update_control_panel()
                return
        
        print("未找到包含该点的物体")
    
    def get_box_bounds(self, data):
        """根据数据计算盒子边界"""
        center = data['middle-point']
        l = data['length']['value'] / 2
        w = data['width']['value'] / 2
        h = data['height']['value'] / 2
        
        return [
            center[0] - l, center[0] + l,
            center[1] - w, center[1] + w,
            center[2] - h, center[2] + h
        ]


    def create_box(self, obj_name, data):
        """根据数据创建长方体"""
        center = data['middle-point']
        dimensions = [
            data['length']['value'], 
            data['width']['value'], 
            data['height']['value']
        ]
        box = pv.Box(
            bounds=[
                center[0]-dimensions[0]/2, center[0]+dimensions[0]/2,
                center[1]-dimensions[1]/2, center[1]+dimensions[1]/2,
                center[2]-dimensions[2]/2, center[2]+dimensions[2]/2
            ]
        )
        return box

    def update_visualization(self):
        """更新3D可视化（关键修改点3：使用plotter正确方法）"""
        self.plotter.clear()
        for obj_name, obj_data in self.data.items():
            box = self.create_box(obj_name, obj_data)
            color = self.get_color(obj_data['category'])
            self.plotter.add_mesh(
                box, 
                name=obj_name,
                color=color,
                opacity=0.8,
                show_edges=True
            )
        self.plotter.reset_camera()

    def get_color(self, category):
        """根据类别获取颜色"""
        colors = {
            '床': 'lightblue',
            '衣柜': 'brown',
            '书桌': 'tan',
            '椅子': 'orange',
            '其他': 'gray'
        }
        return colors.get(category, 'white')

    def select_object(self, surface, point):
        """选择物体时的回调函数（关键修改点4：通过plotter访问picked_actor）"""
        picked = self.plotter.picked_actor
        if picked is not None:
            self.current_obj = picked.name
            self.update_control_panel()

    def update_control_panel(self):
        """更新控制面板显示"""
        if self.current_obj:
            data = self.data[self.current_obj]
            self.lbl_name.setText(f"当前选择: {self.current_obj}")
            self.cmb_category.setCurrentText(data['category'])
            self.txt_material.setText(data['material'])
            pos = data['middle-point']
            self.txt_position.setText(f"{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}")
            dims = [
                data['length']['value'],
                data['width']['value'],
                data['height']['value']
            ]
            self.txt_dimensions.setText(f"{dims[0]:.2f}, {dims[1]:.2f}, {dims[2]:.2f}")

    def save_changes(self):
        """保存当前修改"""
        if self.current_obj:
            # 更新数据
            data = self.data[self.current_obj]
            data['category'] = self.cmb_category.currentText()
            data['material'] = self.txt_material.text()
            
            # 更新位置和尺寸
            try:
                new_pos = list(map(float, self.txt_position.text().split(',')))
                data['middle-point'] = new_pos
                new_dims = list(map(float, self.txt_dimensions.text().split(',')))
                data['length']['value'] = new_dims[0]
                data['width']['value'] = new_dims[1]
                data['height']['value'] = new_dims[2]
            except Exception as e:
                print("输入格式错误:", e)
            
            # 更新可视化
            self.update_visualization()

    def get_graph(self):
        #由更新后的数据更新图结构
        s = 0

    def export_data(self):
        """导出修改后的数据"""
        options = QFileDialog.Options()
        path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "JSON Files (*.json)", options=options
        )
        if path:
            # 转换数据格式
            export_metadata = {}
            for name, data in self.data.items():
                export_metadata[name] = {
                    "category": data['category'],
                    "middle-point": data['middle-point'],
                    "rotate": data['rotate'],
                    "length": data['length'],
                    "width": data['width'],
                    "height": data['height'],
                    "material": data['material']
                }
            
            with open(path, 'w') as f:
                json.dump(export_metadata, f, indent=2, ensure_ascii=False)
            
            #模板2，下面是由编辑后的css描述，得到对应的英文描述
            request_template2 = "我给你一段CSS样式描述，请根据我给的内容用英文简要描述这个房间，将各个家具在房间中的大致方位，材质描述出来。房间布局如下："
            user_input = request_template2 + str(export_metadata)
            result = get_chat_response(user_input)#得到返回的信息
            print("\n\n最终方案：\n", result)

            '''
            A_Client = Client(settings.ip_addr,settings.port)
            A_Client.send_msg(result)
            msg_back = A_Client.receive_msg(1024)
            print(msg_back)
            if msg_back == '找到了':
                print(0)

                transtime = A_Client.receive_msg(1024)
                print("接收到的信息是：",transtime)
                size = int(transtime)
                print("将要接收的次数是",size)

                A_Client.recive_img(size)

            # 4、关闭连接（必选的回收资源操作）
            A_Client.close()
            '''


# 使用示例
if __name__ == "__main__":
    os.environ["DEEPSEEK_API_KEY"] = "XXXXXX"#补充自定义的api-key
    
    #模板1，下面是输入需求得到对应的css描述，并且从LLM中提取中css描述对应内容
    request_template1 = "假设你是一个经验丰富的室内装潢设计师，请根据我的描述做出一个符合条件的室内设计方案。其中，室内设计方案以类似CSS语法的格式描述，每个家具可以粗略视为一个盒子对象，里面信息包括类别，盒子的中心位置坐标，相比主轴的旋转角度（选定门所在的墙为主轴方向），盒子的长宽高，材质。参考如下示例.bed { category: '床'; middle-point:(1.6,4,1); rotate: 0deg;length:2.2m;width: 2m;height: 0.6m; material: linen-texture;}。严格按照示例给出的模板，不要少信息，也不要多出额外的信息。CSS相关信息以“--CSS--”开头，结尾处也加上“--CSS--”。我的描述是："
    
    user_input = input("请输入场景描述内容（输入exit退出）: ")
    user_input = request_template1 + user_input
    result = get_chat_response(user_input)#得到返回的信息
    print("\n\n最终方案：\n", result)
    pattern1 = r'--CSS--(.*?)--CSS--'
    matches = re.findall(pattern1, result, re.DOTALL)
    css_data = matches[0]
    print("\n\n得到的CSS数据是：",css_data)


    #从css描述内容，将文本变成格式化的数据
    parsed_data = parse_css_like_data(css_data,output_file="furniture.json")
    print("CSS数据是：",parsed_data)

    #data = json.loads(parsed_data)
    #print(data)
    

    # 启动应用
    app = QApplication([])
    window = ObjectEditor(parsed_data)
    window.show()
    app.exec_()