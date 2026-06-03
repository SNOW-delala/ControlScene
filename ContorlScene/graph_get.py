# coding=utf-8
# 从JSON文件处理得到图结构，并且将结果存在graph_{i}.txt之中
import json

# 读取第一个JSON文件
with open('3397.json', 'r', encoding='utf-8') as f1:
    data1 = json.load(f1)

epsilon = 0.1  # 紧贴容差阈值

# 存储所有middle-point的列表
middle_points_x = []
middle_points_y = []
middle_points_z = []
length = []
width = []
height = []
# 存储序列号（对象键）到对象名称（类别）的字典
serial_to_category = {}
i = 0

# 遍历合并后的数据
for obj_id, obj_info in data1.items():
    middle_points_x.append(obj_info['middle-point'][0])
    middle_points_y.append(obj_info['middle-point'][1])
    middle_points_z.append(obj_info['middle-point'][2])
    length.append(obj_info['length']['value'])
    width.append(obj_info['width']['value'])
    height.append(obj_info['height']['value'])
    serial_to_category[i] = obj_id
    i = i + 1

row = len(middle_points_x)
col = len(middle_points_x)
matrix = [[0 for _ in range(col)] for _ in range(row)]

'''
定义一个矩阵来表示图结构，其中：
matrix[i][j]= 1  表示家具i在家具j的左边;
matrix[i][j]= -1 表示家具i在家具j的右边;
matrix[i][j]= 2  表示家具i在家具j的左边且紧贴;
matrix[i][j]= -2 表示家具i在家具j的右边且紧贴;
matrix[i][j]= 3  表示家具i在家具j的上边;
matrix[i][j]= -3 表示家具i在家具j的下边;
matrix[i][j]= 4  表示家具i在家具j的上边且紧贴;
matrix[i][j]= -4 表示家具i在家具j的下边且紧贴;
matrix[i][j]= 5  表示家具i在家具j的前边;
matrix[i][j]= -5 表示家具i在家具j的后边;
matrix[i][j]= 6  表示家具i在家具j的前边且紧贴;
matrix[i][j]= -6 表示家具i在家具j的后边且紧贴;
x对应length
y对应width
z对应height
'''
for m in range(0,row):
    for n in range(m+1,row):
        m_below = middle_points_z[m] - 1/2 * height[m]#表示m物质的底面
        m_above = middle_points_z[m] + 1/2 * height[m]#表示m物质的顶面
        m_back = middle_points_x[m] - 1/2 * length[m]#表示m物质的后面
        m_front = middle_points_x[m] + 1/2 * length[m]#表示m物质的前面
        m_left = middle_points_y[m] - 1/2 * width[m]#表示m物质的左面
        m_right = middle_points_y[m] + 1/2 * width[m]#表示m物质的右面


        n_below = middle_points_z[n] - 1/2 * height[n]#表示n物质的底面
        n_above = middle_points_z[n] + 1/2 * height[n]#表示n物质的顶面
        n_back = middle_points_x[n] - 1/2 * length[n]#表示n物质的后面
        n_front = middle_points_x[n] + 1/2 * length[n]#表示n物质的前面
        n_left = middle_points_y[n] - 1/2 * width[n]#表示n物质的左面
        n_right = middle_points_y[n] + 1/2 * width[n]#表示n物质的右面

        # 检查上紧贴（m在n上且底面接近n顶面）
        if m_below >= n_above - epsilon and abs(m_below - n_above) <= epsilon:
            matrix[m][n] = 4
            matrix[n][m] = -4
        # 检查下紧贴（m在n下且顶面接近n底面）
        elif m_above <= n_below + epsilon and abs(m_above - n_below) <= epsilon:
            matrix[m][n] = -4
            matrix[n][m] = 4
        # 常规上下关系判断
        elif m_below >= n_above:  # m在n上方（非紧贴）
            matrix[m][n] = 3
            matrix[n][m] = -3
        elif m_above <= n_below:  # m在n下方（非紧贴）
            matrix[m][n] = -3
            matrix[n][m] = 3
        else:
            # ========== 处理左右关系 ==========
            # 检查左紧贴（m在n左且右侧接近n左侧）
            if m_right <= n_left + epsilon and abs(m_right - n_left) <= epsilon:
                matrix[m][n] = 2
                matrix[n][m] = -2
            # 检查右紧贴（m在n右且左侧接近n右侧）
            elif m_left >= n_right - epsilon and abs(m_left - n_right) <= epsilon:
                matrix[m][n] = -2
                matrix[n][m] = 2
            # 常规左右关系判断
            elif m_right <= n_left:  # m在n左侧（非紧贴）
                matrix[m][n] = 1
                matrix[n][m] = -1
            elif m_left >= n_right:  # m在n右侧（非紧贴）
                matrix[m][n] = -1
                matrix[n][m] = 1
            else:
                # ========== 处理前后关系 ==========
                # 检查前紧贴（m在n前且后侧接近n前侧）
                if m_back >= n_front - epsilon and abs(m_back - n_front) <= epsilon:
                    matrix[m][n] = 6
                    matrix[n][m] = -6
                # 检查后紧贴（m在n后且前侧接近n后侧）
                elif m_front <= n_back + epsilon and abs(m_front - n_back) <= epsilon:
                    matrix[m][n] = -6
                    matrix[n][m] = 6
                # 常规前后关系判断
                elif m_back >= n_front:  # m在n前方（非紧贴）
                    matrix[m][n] = 5
                    matrix[n][m] = -5
                elif m_front <= n_back:  # m在n后方（非紧贴）
                    matrix[m][n] = -5
                    matrix[n][m] = 5
print(serial_to_category)
print(matrix)



# 输出结果
'''
print("所有x的列表：")
print(middle_points_x)
print("\n所有y的列表：")
print(middle_points_y)
print("\n所有z的列表：")
print(middle_points_z)
print("\n所有length的列表：")
print(length)
print("\n所有width的列表：")
print(width)
print("\n所有height的列表：")
print(height)
print("\n序列号到对象名称的字典：")
print(serial_to_category)
'''