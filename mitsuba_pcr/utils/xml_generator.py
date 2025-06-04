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
    添加一个通用常量发射器。

    此函数创建一个向所有方向均匀发射指定辐射亮度的光源。
    注意：此函数是一个通用工具。在当前的 `generate_scene_xml` 实现中，
    场景的主要背景/环境光由 `add_background` 函数创建。
    此 `add_constant_emitter` 函数未被 `generate_scene_xml` 用于创建主要背景或当前激活的独立补光。
    之前的注释 "注意：此函数目前未被使用，保留以备将来可能的用途。背景光照现在由add_background函数处理。" 仍然适用。
    
    参数:
        scene (Element): 场景根元素。
        radiance (tuple): RGB元组，定义发射器的辐射亮度。
    
    返回:
        Element: 添加的常量发射器元素。
    """
    emitter = ET.SubElement(scene, "emitter")
    emitter.set("type", "constant")
    
    rgb = ET.SubElement(emitter, "rgb")
    rgb.set("name", "radiance")
    rgb.set("value", f"{radiance[0]},{radiance[1]},{radiance[2]}")
    
    return emitter

def add_background(scene, color=(1, 1, 1)):
    """
    添加恒定颜色的背景发射器。

    此函数创建Mitsuba场景中的唯一环境发射器。其辐射亮度由 `color` 参数直接定义。
    这个发射器既作为相机直接可见的背景（例如天空），也作为场景全局环境光的主要来源。
    
    参数:
        scene (Element): 场景根元素。
        color (tuple): RGB元组，定义发射器的辐射亮度。
    
    返回:
        Element: 添加的背景发射器元素。
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
    为场景添加一个通用的表面材质 (BSDF)。

    此函数创建一个 'roughplastic' 类型的BSDF，具有预设的属性。
    它被赋予ID "surfaceMaterial"，主要被 `add_ground_plane` 函数（用于创建原始的、非贴附的地面）引用。
    
    参数:
        scene (Element): 场景根元素。
    
    返回:
        Element: 添加的BSDF (材质) 元素。
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
    添加面光源 (Area Light)。

    这是场景中的主要方向性光源，用于产生阴影。
    
    参数:
        scene (Element): 场景根元素。
        size (float): 光源的尺寸 (通常是正方形的一边长度)。
                      在 `generate_scene_xml` 中，此值可能来自 `config['light_params']['size']`，
                      若未在配置中提供，则使用此函数的默认值。
        height (float): 光源的高度位置。
                      在 `generate_scene_xml` 中，此值可能来自 `config['light_params']['height']`，
                      若未在配置中提供，则使用此函数的默认值。
        intensity (float): 光源的辐射强度。每个RGB通道将使用此强度值。
                         在 `generate_scene_xml` 中，此值来自 `config['light_params']['intensity']`。
    
    返回:
        Element: 添加的面光源形状元素。
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
    添加一个贴附在点云下方的平面，该平面会根据相机视角（如果提供相机参数）调整其方向和位置。

    此平面使用一个纯漫反射 (diffuse) 材质，反射率(reflectance)设置为 (1.0, 1.0, 1.0)，以确保
    在充分光照下能呈现纯白色，从而更好地与纯白背景融合。
    
    参数:
        scene (Element): 场景根元素。
        points (numpy.ndarray): 点云坐标，用于确定平面的基础高度。
        size (float): 平面的基础尺寸。
                      在 `generate_scene_xml` 中，此值来自 `config['attached_ground_params']['size']`。
                      注意：函数内部可能会对此尺寸进行缩放 (e.g., `actual_size = size * 5`) 以确保覆盖范围。
        offset (float): 平面相对于点云在特定方向（通常是z轴或相机up向量反方向）上投影的最低点的偏移量。
                      在 `generate_scene_xml` 中，此值来自 `config['attached_ground_params']['offset']`。
        camera_params (dict, optional): 相机参数字典，包含 'origin', 'target', 'up' NumPy数组。
                                      如果提供，平面将对齐到与相机up向量垂直的方向，并基于点云在up向量上的
                                      投影来确定位置。如果为None，则使用点云的Z轴最低点来定位平面。
    
    返回:
        Element or None: 添加的贴附地面形状元素；如果点云数据为空，则返回None。
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
    生成完整的Mitsuba场景XML。

    参数:
        config (dict): 配置参数字典，主要键包括:
            - 'integrator_type' (str): 积分器类型 ('path'或'direct')。
            - 'samples_per_pixel' (int): 每像素采样数。
            - 'max_depth' (int): 最大光线深度。
            - 'film_width', 'film_height' (int): 输出图像尺寸。
            - 'fov' (float): 视场角。
            - 'origin', 'target', 'up' (list): 相机参数。
            - 'points' (numpy.ndarray): 点云坐标。
            - 'colors' (numpy.ndarray): 点云颜色。
            - 'point_radius' (float): 点半径。
            - 'include_ground' (bool): 是否包含固定的原始地面。
            - 'ground_params' (dict): 原始地面参数 (如果使用)。
            - 'include_area_light' (bool): 是否包含面光源。
            - 'light_params' (dict): 面光源参数，包含:
                - 'intensity' (float): 面光源的强度。
                - 'size' (float): 面光源的大小 (注：此参数预期从config传入，但当前add_area_light函数可能使用固定值或其内部默认值，需检查该函数实现)。
            - 'attach_ground' (bool): 是否添加贴附地面。
            - 'attached_ground_params' (dict): 贴附地面参数。
            - 'background_color' (tuple): RGB元组，定义唯一环境发射器（背景天空）的辐射亮度。
                                         这既是直接可见的背景颜色，也是场景全局环境光的主要来源。
            - 'env_light_intensity' (float): 预期用于控制独立环境补光。由于Mitsuba场景限制为单个环境发射器，
                                            且该发射器已由'background_color'定义，此参数当前在场景生成中未被激活以添加额外光源。
    返回:
        str: 完整的XML场景描述。
    """
    # 默认参数
    integrator_type = config.get('integrator_type', 'path')
    samples_per_pixel = config.get('samples_per_pixel', 256)
    max_depth = config.get('max_depth', -1)
    film_width = config.get('film_width', 3840)
    film_height = config.get('film_height', 2160)
    fov = config.get('fov', 91.49)
    
    origin = config.get('origin', [0, -4, 2])
    target = config.get('target', [0, 0, 0])
    up = config.get('up', [0, 0, 1])
    
    camera_params = {
        'origin': origin,
        'target': target,
        'up': up
    }
    
    scene = create_scene_element()
    
    integrator = add_integrator(scene, integrator_type, max_depth)
    
    if integrator_type == "path":
        hide_emitters = ET.SubElement(integrator, "boolean")
        hide_emitters.set("name", "hideEmitters")
        hide_emitters.set("value", "false") # 确保主要光源和背景可见
    
    # 设置背景发射器：颜色由 background_color 决定，它也是主要的环境光来源。
    background_color_val = config.get('background_color', (1, 1, 1))
    add_background(scene, background_color_val)
    
    # env_light_intensity 当前不用于添加额外的独立环境光，
    # 因为场景限制为单个环境发射器（已由 add_background 创建）。
    # 如需调整整体环境光水平，应直接调整 background_color_val 的亮度。
    # env_intensity_val = config.get('env_light_intensity', 1.0)
    # if env_intensity_val > 0 and env_intensity_val != 1.0: # 避免重复添加或数值混乱
    # print(f"注意: env_light_intensity ({env_intensity_val}) 当前不用于添加独立环境光。")

    add_perspective_sensor(scene, origin, target, up, fov, film_width, film_height, samples_per_pixel)
    add_surface_material(scene) # 为原始地面（如果使用）添加通用表面材质
    
    if 'points' in config:
        add_point_cloud(
            scene, 
            config['points'], 
            config.get('colors', None), 
            config.get('point_radius', 0.006)
        )
    
    if config.get('include_ground', True):
        ground_params = config.get('ground_params', {})
        size = ground_params.get('size', 10)
        height = ground_params.get('height', -0.5)
        add_ground_plane(scene, size, height)
    
    if config.get('attach_ground', False) and 'points' in config:
        attached_ground_params = config.get('attached_ground_params', {})
        size = attached_ground_params.get('size', 15)
        offset = attached_ground_params.get('offset', -0.05)
        add_attached_ground_plane(scene, config['points'], size, offset, camera_params)
    
    if config.get('include_area_light', True):
        light_params = config.get('light_params', {})
        # 从light_params获取强度；大小和高度使用函数默认值或硬编码值（如果light_params中没有传递）
        intensity = light_params.get('intensity', 3) 
        size = light_params.get('size', 10) # 尝试从config获取，否则使用默认值
        height = light_params.get('height', 20) # 尝试从config获取，否则使用默认值
        add_area_light(scene, size, height, intensity)
    
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