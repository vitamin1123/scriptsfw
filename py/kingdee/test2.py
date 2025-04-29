import xml.etree.ElementTree as ET

# 解析XML文件
file_path = input("请输入XML文件路径：")
tree = ET.parse(file_path)
root = tree.getroot()

# 找到Resources下的wf_resource元素
resources = root.find('Resources')
if resources is not None:
    wf_resource = resources.find('wf_resource')
    if wf_resource is not None:
        # 找到data元素
        data = wf_resource.find('data')
        if data is not None:
            # 获取data元素的文本内容
            data_content = data.text
            print(data_content)
        else:
            print("未找到data元素。")
    else:
        print("未找到wf_resource元素。")
else:
    print("未找到Resources元素。")