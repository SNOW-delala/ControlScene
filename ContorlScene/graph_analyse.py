import base64
from openai import OpenAI

def image_to_base64(image_path):
    """将本地图片转换为Base64编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 初始化客户端
client = OpenAI(
    api_key="XXXX",
    base_url="https://api.siliconflow.cn/v1"
)

# 本地图片路径（修改为你的实际路径）
local_image_path = "./e9zR4mvMWw7_270/pano.jpg"  # 支持jpg/png格式

# 构建请求
response = client.chat.completions.create(
    model="deepseek-ai/deepseek-vl2",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        # 使用Base64编码的本地图片
                        "url": f"data:image/jpeg;base64,{image_to_base64(local_image_path)}"
                    }
                },
                {
                    "type": "text",
                    "text": """请完成以下分析：
1. 用一段英文描述这张场景图的内容，说明画面风格特征，列举所有可见家具及大概位置
2. 用英文一句话列举图中所有的家具，将家具编号并描述对应的材质，类似于这样的形式towel-rack:stainless-steel
3. 用中文简要叙述2中每个家具之间的位置关系"""
                }
            ]
        }
    ],
    temperature=0.3,  # 降低随机性使描述更准确
    max_tokens=1024,
    stream=True
)

# 处理流式响应
full_response = []
for chunk in response:
    if chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        full_response.append(content)
        print(content, end="", flush=True)  # 实时输出

# 最终结果保存
print("\n\n完整分析结果：")
print(''.join(full_response))