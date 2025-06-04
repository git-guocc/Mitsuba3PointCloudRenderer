"""
XML场景生成模块

使用xml.etree.ElementTree库生成Mitsuba2渲染引擎所需的XML场景描述文件。
"""

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import numpy as np

def prettify_xml(elem):
    """
    将ElementTree元素转换为格式化的XML字符串
    
    参数:
        elem: ElementTree元素
    
    返回:
        str: 格式化的XML字符串
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ").replace('<?xml version="1.0" ?>\n', '')

def create_scene_element():
    """
    创建场景根元素
    
    返回:
        Element: 场景根元素
    """
    scene = ET.Element("scene")
    scene.set("version", "0.6.0")
    return scene

def add_constant_emitter(scene, radiance=(1, 1, 1)):
    """
    添加常量发光体，用于提供均匀的背景光照
    注意：此函数目前未被使用，保留以备将来可能的用途。背景光照现在由add_background函数处理。
    
    参数:
        scene (Element): 场景元素
        radiance (tuple): RGB辐射值
    
    返回:
        Element: 添加的发光体元素
    """
    emitter = ET.SubElement(scene, "emitter")
    emitter.set("type", "constant")
    
    rgb = ET.SubElement(emitter, "rgb")
    rgb.set("name", "radiance")
    rgb.set("value", f"{radiance[0]},{radiance[1]},{radiance[2]}")
    
    return emitter

def add_background(scene, color=(1, 1, 1)):
    """
    添加背景，确保渲染时有一个一致的背景色
    
    参数:
        scene (Element): 场景元素
        color (tuple): RGB颜色值
    
    返回:
        Element: 添加的背景元素
    """
    # 创建一个常量发射器作为背景
    emitter = ET.SubElement(scene, "emitter")
    emitter.set("type", "constant")
    
    # 设置背景颜色
    rgb = ET.SubElement(emitter, "rgb")
    rgb.set("name", "radiance")
    rgb.set("value", f"{color[0]},{color[1]},{color[2]}")
    
    return emitter

def add_integrator(scene, integrator_type="path", max_depth=-1):
    """
    添加积分器
    
    参数:
        scene (Element): 场景元素
        integrator_type (str): 积分器类型，'path'或'direct'
        max_depth (int): 最大光线深度，仅对path积分器有效
    
    返回:
        Element: 添加的积分器元素
    """
    integrator = ET.SubElement(scene, "integrator")
    integrator.set("type", integrator_type)
    
    if integrator_type == "path" and max_depth > 0:
        max_depth_elem = ET.SubElement(integrator, "integer")
        max_depth_elem.set("name", "maxDepth")
        max_depth_elem.set("value", str(max_depth))
    
    return integrator

def add_perspective_sensor(scene, origin, target, up, fov, film_width, film_height, samples_per_pixel):
    """
    添加透视相机
    
    参数:
        scene (Element): 场景元素
        origin (tuple): 相机原点坐标
        target (tuple): 相机目标点坐标
        up (tuple): 相机上方向
        fov (float): 视场角（度）
        film_width (int): 输出图像宽度
        film_height (int): 输出图像高度
        samples_per_pixel (int): 每像素采样数
    
    返回:
        Element: 添加的相机元素
    """
    sensor = ET.SubElement(scene, "sensor")
    sensor.set("type", "perspective")
    
    # 远近裁剪面
    far_clip = ET.SubElement(sensor, "float")
    far_clip.set("name", "farClip")
    far_clip.set("value", "100")
    
    near_clip = ET.SubElement(sensor, "float")
    near_clip.set("name", "nearClip")
    near_clip.set("value", "0.1")
    
    # 相机变换
    transform = ET.SubElement(sensor, "transform")
    transform.set("name", "toWorld")
    
    # 确保坐标是有效的浮点数
    origin_str = f"{float(origin[0])},{float(origin[1])},{float(origin[2])}"
    target_str = f"{float(target[0])},{float(target[1])},{float(target[2])}"
    up_str = f"{float(up[0])},{float(up[1])},{float(up[2])}"
    
    # 检查相机位置和目标点不能相同
    if origin_str == target_str:
        print("警告: 相机位置和目标点相同，调整目标点位置")
        target_list = list(map(float, target))
        target_list[2] += 0.1  # 稍微调整Z轴
        target_str = f"{target_list[0]},{target_list[1]},{target_list[2]}"
    
    lookat = ET.SubElement(transform, "lookat")
    lookat.set("origin", origin_str)
    lookat.set("target", target_str)
    lookat.set("up", up_str)
    
    # 视场角
    fov_elem = ET.SubElement(sensor, "float")
    fov_elem.set("name", "fov")
    fov_elem.set("value", str(fov))
    
    # 采样器
    sampler = ET.SubElement(sensor, "sampler")
    sampler.set("type", "independent")
    
    sample_count = ET.SubElement(sampler, "integer")
    sample_count.set("name", "sampleCount")
    sample_count.set("value", str(samples_per_pixel))
    
    # 胶片
    film = ET.SubElement(sensor, "film")
    film.set("type", "hdrfilm")
    
    width = ET.SubElement(film, "integer")
    width.set("name", "width")
    width.set("value", str(film_width))
    
    height = ET.SubElement(film, "integer")
    height.set("name", "height")
    height.set("value", str(film_height))
    
    rfilter = ET.SubElement(film, "rfilter")
    rfilter.set("type", "gaussian")
    
    return sensor

def add_surface_material(scene):
    """
    添加表面材质
    
    参数:
        scene (Element): 场景元素
    
    返回:
        Element: 添加的材质元素
    """
    bsdf = ET.SubElement(scene, "bsdf")
    bsdf.set("type", "roughplastic")
    bsdf.set("id", "surfaceMaterial")
    
    distribution = ET.SubElement(bsdf, "string")
    distribution.set("name", "distribution")
    distribution.set("value", "ggx")
    
    alpha = ET.SubElement(bsdf, "float")
    alpha.set("name", "alpha")
    alpha.set("value", "0.05")
    
    int_ior = ET.SubElement(bsdf, "float")
    int_ior.set("name", "intIOR")
    int_ior.set("value", "1.46")
    
    diffuse = ET.SubElement(bsdf, "rgb")
    diffuse.set("name", "diffuseReflectance")
    diffuse.set("value", "1,1,1")
    
    return bsdf

def add_point_cloud(scene, points, colors, point_radius=0.006):
    """
    添加点云
    
    参数:
        scene (Element): 场景元素
        points (numpy.ndarray): 点坐标，形状为(N, 3)
        colors (numpy.ndarray): 点颜色，形状为(N, 3)，范围[0, 1]
        point_radius (float): 点半径
    
    返回:
        list: 添加的点元素列表
    """
    if points is None or points.shape[0] == 0:
        return []
    
    spheres = []
    for i in range(points.shape[0]):
        point = points[i]
        
        # 获取颜色
        if colors is not None and i < colors.shape[0]:
            color = colors[i]
        else:
            color = [0.7, 0.7, 0.7]  # 默认颜色
        
        # 创建球体
        sphere = ET.SubElement(scene, "shape")
        sphere.set("type", "sphere")
        
        radius = ET.SubElement(sphere, "float")
        radius.set("name", "radius")
        radius.set("value", str(point_radius))
        
        transform = ET.SubElement(sphere, "transform")
        transform.set("name", "toWorld")
        
        translate = ET.SubElement(transform, "translate")
        translate.set("x", str(point[0]))
        translate.set("y", str(point[1]))
        translate.set("z", str(point[2]))
        
        # 添加材质
        bsdf = ET.SubElement(sphere, "bsdf")
        bsdf.set("type", "diffuse")
        
        rgb = ET.SubElement(bsdf, "rgb")
        rgb.set("name", "reflectance")
        rgb.set("value", f"{color[0]},{color[1]},{color[2]}")
        
        spheres.append(sphere)
    
    return spheres

def add_ground_plane(scene, size=10, height=-0.5):
    """
    添加地面平面
    
    参数:
        scene (Element): 场景元素
        size (float): 平面大小
        height (float): 平面高度
    
    返回:
        Element: 添加的平面元素
    """
    shape = ET.SubElement(scene, "shape")
    shape.set("type", "rectangle")
    
    ref = ET.SubElement(shape, "ref")
    ref.set("name", "bsdf")
    ref.set("id", "surfaceMaterial")
    
    transform = ET.SubElement(shape, "transform")
    transform.set("name", "toWorld")
    
    scale = ET.SubElement(transform, "scale")
    scale.set("x", str(size))
    scale.set("y", str(size))
    scale.set("z", "1")
    
    translate = ET.SubElement(transform, "translate")
    translate.set("x", "0")
    translate.set("y", "0")
    translate.set("z", str(height))
    
    return shape

def add_area_light(scene, size=10, height=20, intensity=3):
    """
    添加面光源
    
    参数:
        scene (Element): 场景元素
        size (float): 光源大小
        height (float): 光源高度
        intensity (float): 光源强度
    
    返回:
        Element: 添加的光源元素
    """
    shape = ET.SubElement(scene, "shape")
    shape.set("type", "rectangle")
    
    transform = ET.SubElement(shape, "transform")
    transform.set("name", "toWorld")
    
    scale = ET.SubElement(transform, "scale")
    scale.set("x", str(size))
    scale.set("y", str(size))
    scale.set("z", "1")
    
    lookat = ET.SubElement(transform, "lookat")
    # 确保坐标是有效的浮点数
    origin_str = f"{float(-4)},{float(4)},{float(height)}"
    target_str = f"{float(0)},{float(0)},{float(0)}"
    up_str = f"{float(0)},{float(0)},{float(1)}"
    
    lookat.set("origin", origin_str)
    lookat.set("target", target_str)
    lookat.set("up", up_str)
    
    emitter = ET.SubElement(shape, "emitter")
    emitter.set("type", "area")
    
    rgb = ET.SubElement(emitter, "rgb")
    rgb.set("name", "radiance")
    rgb.set("value", f"{intensity},{intensity},{intensity}")
    
    return shape

def add_attached_ground_plane(scene, points, size=10, offset=-0.01, camera_params=None):
    """
    添加一个贴附在点云下方的平面，并根据相机视角进行调整
    
    参数:
        scene (Element): 场景元素
        points (numpy.ndarray): 点云坐标，用于确定平面位置
        size (float): 平面大小
        offset (float): 平面相对于点云最低点的偏移量
        camera_params (dict): 相机参数，包含origin, target, up
    
    返回:
        Element: 添加的平面元素
    """
    if points is None or points.shape[0] == 0:
        return None
    
    # 创建平面
    shape = ET.SubElement(scene, "shape")
    shape.set("type", "rectangle")
    
    # 使用自定义材质，而不是引用全局材质
    bsdf = ET.SubElement(shape, "bsdf")
    bsdf.set("type", "diffuse")
    
    # 设置漫反射材质属性 (纯漫反射只有一个主要参数: reflectance)
    reflectance = ET.SubElement(bsdf, "rgb")
    reflectance.set("name", "reflectance")
    reflectance.set("value", "1.0,1.0,1.0")
    
    transform = ET.SubElement(shape, "transform")
    transform.set("name", "toWorld")
    
    # 使平面足够大，确保能覆盖整个点云
    actual_size = size * 5  # 进一步增大平面尺寸
    scale = ET.SubElement(transform, "scale")
    scale.set("x", str(actual_size))
    scale.set("y", str(actual_size))
    scale.set("z", "1")
    
    # 如果提供了相机参数，根据相机视角调整平面
    if camera_params and 'origin' in camera_params and 'target' in camera_params and 'up' in camera_params:
        origin = np.array(camera_params['origin'])
        target = np.array(camera_params['target'])
        up = np.array(camera_params['up'])
        
        # 归一化up向量
        up = up / np.linalg.norm(up)
        
        # 计算点云在up向量方向上的投影的最小值
        projections = np.dot(points, up)
        min_proj = np.min(projections)
        
        # 计算平面上的一个点（在最小投影点下方offset距离）
        # 增加偏移量，确保平面位于点云下方足够远的位置
        plane_point = min_proj * up + offset * 2 * up
        
        # 创建lookat变换，使平面与up向量垂直
        lookat = ET.SubElement(transform, "lookat")
        
        # 计算lookat的三个参数
        lookat_origin = plane_point.tolist()
        lookat_target = (plane_point + up).tolist()
        
        # 计算相机视线方向
        view_dir = target - origin
        view_dir = view_dir / np.linalg.norm(view_dir)
        
        # 计算lookat的up向量（与up向量和视线方向都垂直）
        lookat_up = np.cross(up, view_dir)
        if np.linalg.norm(lookat_up) < 0.1:
            # 如果叉积太小，选择另一个方向
            lookat_up = np.cross(up, [1, 0, 0])
            if np.linalg.norm(lookat_up) < 0.1:
                lookat_up = np.cross(up, [0, 1, 0])
        lookat_up = lookat_up / np.linalg.norm(lookat_up)
        
        lookat.set("origin", f"{lookat_origin[0]},{lookat_origin[1]},{lookat_origin[2]}")
        lookat.set("target", f"{lookat_target[0]},{lookat_target[1]},{lookat_target[2]}")
        lookat.set("up", f"{lookat_up[0]},{lookat_up[1]},{lookat_up[2]}")
    else:
        # 如果没有相机参数，使用默认的平面位置
        # 计算点云的最低点（z坐标最小的点）
        min_z = np.min(points[:, 2])
        plane_height = min_z + offset * 2  # 增加偏移量
        
        translate = ET.SubElement(transform, "translate")
        translate.set("x", "0")
        translate.set("y", "0")
        translate.set("z", str(plane_height))
    
    return shape

def generate_scene_xml(config):
    """
    生成完整的Mitsuba场景XML
    
    参数:
        config (dict): 配置参数字典，包含:
            - integrator_type (str): 积分器类型，'path'或'direct'
            - samples_per_pixel (int): 每像素采样数
            - max_depth (int): 最大光线深度
            - film_width (int): 输出图像宽度
            - film_height (int): 输出图像高度
            - fov (float): 视场角（度）
            - origin (list): 相机原点坐标 [x, y, z]
            - target (list): 相机目标点坐标 [x, y, z]
            - up (list): 相机上方向 [x, y, z]
            - points (numpy.ndarray): 点坐标
            - colors (numpy.ndarray): 点颜色
            - point_radius (float): 点半径
            - include_ground (bool): 是否包含地面
            - ground_params (dict): 地面参数
            - include_area_light (bool): 是否包含面光源
            - light_params (dict): 光源参数
            - attach_ground (bool): 是否添加贴附在点云下方的平面
            - attached_ground_params (dict): 贴附平面参数
            - env_light_intensity (float): 环境光强度
            - background_color (tuple): 背景颜色 (r, g, b)
    
    返回:
        str: 完整的XML场景描述
    """
    # 默认参数
    integrator_type = config.get('integrator_type', 'path')
    samples_per_pixel = config.get('samples_per_pixel', 256)
    max_depth = config.get('max_depth', -1)
    film_width = config.get('film_width', 3840)
    film_height = config.get('film_height', 2160)
    fov = config.get('fov', 91.49)
    
    # 相机参数
    origin = config.get('origin', [0, -4, 2])  # 更好的默认相机位置
    target = config.get('target', [0, 0, 0])
    up = config.get('up', [0, 0, 1])
    
    # 创建相机参数字典
    camera_params = {
        'origin': origin,
        'target': target,
        'up': up
    }
    
    # 创建场景
    scene = create_scene_element()
    
    # 添加积分器
    integrator = add_integrator(scene, integrator_type, max_depth)
    
    # 设置积分器的特殊参数，以解决背景问题
    if integrator_type == "path":
        # 添加hideEmitters参数，防止直接看到发光体
        # 设置为true可以隐藏发光体本身，使其仅贡献间接光照，有助于实现均匀背景
        # 注意：如果背景也是一个emitter（例如constant emitter），此设置也会隐藏背景emitter
        hide_emitters = ET.SubElement(integrator, "boolean")
        hide_emitters.set("name", "hideEmitters")
        hide_emitters.set("value", "false")
    
    # 添加背景/环境光
    background_color = config.get('background_color', (1, 1, 1))
    
    # 背景发射器直接使用 background_color
    add_background(scene, background_color)
    
    # 添加相机
    add_perspective_sensor(scene, origin, target, up, fov, film_width, film_height, samples_per_pixel)
    
    # 添加表面材质
    add_surface_material(scene)
    
    # 添加点云
    if 'points' in config:
        add_point_cloud(
            scene, 
            config['points'], 
            config.get('colors', None), 
            config.get('point_radius', 0.006)
        )
    
    # 添加地面（如果需要）
    if config.get('include_ground', True):
        ground_params = config.get('ground_params', {})
        size = ground_params.get('size', 10)
        height = ground_params.get('height', -0.5)
        add_ground_plane(scene, size, height)
    
    # 添加贴附在点云下方的平面（如果需要）
    if config.get('attach_ground', False) and 'points' in config:
        attached_ground_params = config.get('attached_ground_params', {})
        size = attached_ground_params.get('size', 15)
        offset = attached_ground_params.get('offset', -0.05)
        add_attached_ground_plane(scene, config['points'], size, offset, camera_params)
    
    # 添加面光源（如果需要）
    if config.get('include_area_light', True):
        light_params = config.get('light_params', {})
        size = light_params.get('size', 10)
        height = light_params.get('height', 20)
        intensity = light_params.get('intensity', 3)
        add_area_light(scene, size, height, intensity)
    
    # 生成格式化的XML字符串
    return prettify_xml(scene)

def save_scene_xml(xml_content, output_file):
    """
    将XML场景内容保存到文件
    
    参数:
        xml_content (str): XML场景内容
        output_file (str): 输出文件路径
    
    返回:
        bool: 保存是否成功
    """
    try:
        with open(output_file, 'w') as f:
            f.write(xml_content)
        print(f"XML场景已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"保存XML场景到 '{output_file}' 时发生错误: {e}")
        return False

def update_camera_in_xml(xml_content, origin, target, up):
    """
    更新XML中的相机参数
    
    参数:
        xml_content (str): 原始XML内容
        origin (list): 相机原点坐标 [x, y, z]
        target (list): 相机目标点坐标 [x, y, z]
        up (list): 相机上方向 [x, y, z]
    
    返回:
        str: 更新后的XML内容
    """
    try:
        # 解析XML
        root = ET.fromstring(xml_content)
        
        # 查找lookat元素
        lookat_elem = root.find(".//lookat")
        if lookat_elem is not None:
            # 更新lookat属性
            lookat_elem.set("origin", f"{origin[0]},{origin[1]},{origin[2]}")
            lookat_elem.set("target", f"{target[0]},{target[1]},{target[2]}")
            lookat_elem.set("up", f"{up[0]},{up[1]},{up[2]}")
            
            # 生成更新后的XML
            return prettify_xml(root)
        else:
            print("警告: 未能在XML中找到相机lookat元素。")
            return xml_content
    except Exception as e:
        print(f"更新相机参数时发生错误: {e}")
        return xml_content 