"""
Mitsuba2 点云渲染模块

提供使用Mitsuba2渲染点云的核心功能。
"""

import os
import subprocess
import numpy as np
import datetime
import tempfile
import shutil
import sys

from .utils.io import load_point_cloud, convert_exr_to_image
from .utils.transform import standardize_bbox, transform_for_mitsuba
from .utils.color import apply_colormap, srgb_to_linear
from .utils.xml_generator import generate_scene_xml, save_scene_xml

# 全局变量存储用户设置的Mitsuba路径
_USER_MITSUBA_PATH = None

def set_mitsuba_path(path):
    """
    设置Mitsuba可执行文件路径
    
    参数:
        path (str): Mitsuba可执行文件的路径
        
    返回:
        bool: 设置是否成功
    """
    global _USER_MITSUBA_PATH
    
    if not os.path.isfile(path):
        print(f"错误: 指定的Mitsuba路径不存在: '{path}'")
        return False
    
    try:
        # 验证路径
        result = subprocess.run([path, '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               check=False)
        if result.returncode == 0:
            _USER_MITSUBA_PATH = path
            print(f"成功设置Mitsuba路径: {path}")
            return True
        else:
            print(f"警告: 指定的路径似乎不是有效的Mitsuba可执行文件: '{path}'")
            print(f"错误信息: {result.stderr}")
            return False
    except Exception as e:
        print(f"错误: 无法验证Mitsuba路径: {e}")
        return False

def find_mitsuba_executable():
    """
    查找Mitsuba可执行文件路径
    
    首先检查全局变量_USER_MITSUBA_PATH，然后检查环境变量MITSUBA_EXECUTABLE，最后检查常见安装路径
    
    返回:
        str: Mitsuba可执行文件路径，如果未找到则返回None
    """
    global _USER_MITSUBA_PATH
    
    # 检查全局变量中设置的路径
    if _USER_MITSUBA_PATH is not None and os.path.isfile(_USER_MITSUBA_PATH):
        print(f"使用已设置的Mitsuba路径: {_USER_MITSUBA_PATH}")
        return _USER_MITSUBA_PATH
    
    # 检查环境变量
    if 'MITSUBA_EXECUTABLE' in os.environ:
        path = os.environ['MITSUBA_EXECUTABLE']
        if os.path.isfile(path):
            print(f"已从环境变量找到Mitsuba: {path}")
            return path
    
    # 检查常见路径
    common_paths = [
        # 用户指定的路径 (最高优先级)
        "C:\\Users\\xxx\\anaconda3\\envs\\PointCloudRender\\Scripts\\mitsuba.exe",
        
        # Conda 环境路径 (对CI环境有用)
        os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Scripts', 'mitsuba.exe'),
        os.path.join(os.environ.get('CONDA_PREFIX', ''), 'bin', 'mitsuba'),
        os.path.join(os.environ.get('CONDA_PREFIX', ''), 'mitsuba'),
        
        # Windows路径
        'mitsuba.exe',
        'C:\\Program Files\\Mitsuba\\mitsuba.exe',
        'C:\\Program Files (x86)\\Mitsuba\\mitsuba.exe',
        os.path.expanduser('~/mitsuba/dist/mitsuba.exe'),
        
        # Linux/macOS路径
        'mitsuba',  # 如果在PATH中
        '/usr/local/bin/mitsuba',
        '/usr/bin/mitsuba',
        os.path.expanduser('~/mitsuba/dist/mitsuba')
    ]
    
    # 首先检查文件是否存在
    for path in common_paths:
        try:
            if path and os.path.isfile(path):
                print(f"已找到Mitsuba: {path}")
                return path
        except Exception:
            # 忽略路径无效的错误
            continue
    
    # 如果文件存在检查失败，尝试运行命令
    for path in common_paths:
        if not path:
            continue
            
        try:
            # 尝试执行带--version参数的命令，检查是否可用
            result = subprocess.run([path, '--version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   check=False)
            if result.returncode == 0:
                print(f"已验证Mitsuba可执行: {path}")
                return path
        except Exception:
            # 忽略错误，继续尝试下一个路径
            continue
    
    # 尝试从PATH中直接查找
    try:
        # 在Windows上
        if sys.platform == 'win32':
            result = subprocess.run(['where', 'mitsuba'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True, 
                                  check=False)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip().split('\n')[0]
                print(f"已从PATH找到Mitsuba: {path}")
                return path
        # 在Linux/macOS上
        else:
            result = subprocess.run(['which', 'mitsuba'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True, 
                                  check=False)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                print(f"已从PATH找到Mitsuba: {path}")
                return path
    except Exception:
        # 忽略错误
        pass
    
    # 为了CI环境的测试，允许MOCK模式
    if os.environ.get('MITSUBA_MOCK', '').lower() in ('true', '1', 'yes'):
        print("警告: 未找到真实的Mitsuba可执行文件，但已启用MOCK模式")
        return "mock_mitsuba"
    
    print("未找到Mitsuba可执行文件，请确保Mitsuba已正确安装")
    return None

def render_point_cloud(args):
    """
    使用Mitsuba2渲染点云
    
    参数:
        args: 命令行参数对象或配置字典，包含:
            - input_file: 输入点云文件路径
            - output_dir: 输出目录
            - output_prefix: 输出文件前缀
            - output_format: 输出图像格式 ('png', 'jpg', 'exr')
            - integrator: 积分器类型 ('path', 'direct')
            - samples: 每像素采样数
            - max_depth: 最大光线深度
            - num_points: 渲染点数
            - point_radius: 点半径
            - color_mode: 颜色模式 ('original', 'colormap', 'fixed')
            - fixed_color: 固定颜色 [R, G, B]
            - camera_params: 相机参数字符串
            - fov: 视场角
            - resolution: 输出分辨率 [width, height]
            - seed: 随机种子
            - cleanup: 是否清理中间文件
            - mitsuba_path: Mitsuba可执行文件路径
            - include_ground: 是否包含地面
            - ci_test_mode: 是否在CI测试模式下运行（不需要真正的Mitsuba）
    
    返回:
        bool: 渲染是否成功
    """
    # 将args转换为字典（如果是argparse.Namespace）
    if not isinstance(args, dict):
        args = vars(args)
    
    # 设置随机种子
    if 'seed' in args and args['seed'] is not None:
        np.random.seed(args['seed'])
    
    # 检查是否为CI测试模式
    ci_test_mode = args.get('ci_test_mode', False)
    if ci_test_mode or os.environ.get('CI_TEST_MODE', '').lower() in ('true', '1', 'yes'):
        ci_test_mode = True
        print("检测到CI测试模式，将跳过实际渲染过程。")
    
    # 查找Mitsuba可执行文件
    mitsuba_path = args.get('mitsuba_path')
    if not mitsuba_path:
        mitsuba_path = find_mitsuba_executable()
        if not mitsuba_path:
            if ci_test_mode:
                print("CI测试模式: 未找到Mitsuba，但将继续处理其他步骤。")
                mitsuba_path = "mock_mitsuba"  # 设置一个占位值以便继续
            else:
                print("错误: 未找到Mitsuba可执行文件。请通过以下方式指定Mitsuba路径:")
                print("1. 使用set_mitsuba_path()函数设置路径")
                print("2. 指定--mitsuba_path命令行参数")
                print("3. 设置MITSUBA_EXECUTABLE环境变量")
                print("4. 修改mitsuba_pcr/render.py中的common_paths列表添加您的Mitsuba路径")
                print("5. 或者设置CI_TEST_MODE=true环境变量以跳过实际渲染")
                return False
    else:
        # 验证用户提供的路径是否有效
        if not os.path.isfile(mitsuba_path) and not ci_test_mode:
            print(f"错误: 指定的Mitsuba路径不存在: '{mitsuba_path}'")
            return False
        
        try:
            # 尝试执行带--version参数的命令，检查是否可用
            if not ci_test_mode and mitsuba_path != "mock_mitsuba":
                result = subprocess.run([mitsuba_path, '--version'], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True, 
                                      check=False)
                if result.returncode != 0:
                    print(f"警告: 指定的Mitsuba路径可能无效: '{mitsuba_path}'")
                    print(f"错误信息: {result.stderr}")
        except Exception as e:
            if not ci_test_mode:
                print(f"警告: 无法验证Mitsuba路径: {e}")
    
    print(f"使用Mitsuba路径: {mitsuba_path}")
    
    # 加载点云
    input_file = args.get('input_file')
    if not input_file:
        print("错误: 未指定输入文件。")
        return False
    
    points, colors = load_point_cloud(input_file)
    if points is None:
        return False
    
    # 准备输出路径
    output_dir = args.get('output_dir', '.')
    os.makedirs(output_dir, exist_ok=True)
    
    output_prefix = args.get('output_prefix')
    if not output_prefix:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
        output_prefix = f"{base_name}_{timestamp}"
    
    output_format = args.get('output_format', 'png').lower()
    xml_file = os.path.join(output_dir, f"{output_prefix}.xml")
    exr_file = os.path.join(output_dir, f"{output_prefix}.exr")
    output_file = os.path.join(output_dir, f"{output_prefix}.{output_format}")
    
    # 处理点云数据
    num_points = args.get('num_points', -1)  # 默认使用所有点
    normalized_points = standardize_bbox(points, num_points)
    transformed_points = transform_for_mitsuba(normalized_points)
    
    # 处理颜色
    color_mode = args.get('color_mode', 'original')
    point_colors = None
    
    if color_mode == 'original' and colors is not None:
        # 使用原始颜色，但需要转换为线性空间
        if colors.shape[0] != normalized_points.shape[0]:
            # 如果点被采样了，颜色也需要相应采样
            if colors.shape[0] == points.shape[0] and normalized_points.shape[0] < points.shape[0]:
                # 找到采样的点的索引
                indices = np.random.choice(points.shape[0], normalized_points.shape[0], replace=False)
                colors = colors[indices]
            else:
                print("警告: 颜色数量与点数量不匹配，将使用默认颜色映射。")
                color_mode = 'position'
        
        if color_mode == 'original':
            # 将sRGB颜色转换为线性颜色
            point_colors = srgb_to_linear(colors)
    
    if color_mode != 'original' or point_colors is None:
        if color_mode == 'fixed' and 'fixed_color' in args:
            # 使用固定颜色
            fixed_color = args['fixed_color']
            # 将sRGB颜色转换为线性颜色
            linear_color = srgb_to_linear(np.array(fixed_color))
            point_colors = np.tile(linear_color, (transformed_points.shape[0], 1))
        else:
            # 使用颜色映射
            point_colors = apply_colormap(normalized_points, mode=color_mode)
    
    # 解析相机参数
    camera_params = args.get('camera_params')
    camera_config = {}
    
    if camera_params:
        try:
            parts = camera_params.split(' ')
            if len(parts) == 3:
                origin = [float(x) for x in parts[0].split(',')]
                target = [float(x) for x in parts[1].split(',')]
                up = [float(x) for x in parts[2].split(',')]
                
                # 验证参数有效性
                if len(origin) != 3 or len(target) != 3 or len(up) != 3:
                    raise ValueError("相机参数必须是三维坐标")
                
                # 检查相机位置和目标点不能相同
                if origin == target:
                    print("警告: 相机位置和目标点相同，调整目标点位置")
                    target[2] += 0.1  # 稍微调整Z轴
                
                camera_config = {
                    'origin': origin,
                    'target': target,
                    'up': up
                }
                print(f"使用自定义相机设置: 位置={origin}, 目标={target}, 上方向={up}")
            else:
                print(f"警告: 相机参数格式不正确，需要3个部分，但得到了{len(parts)}个。将使用默认相机设置。")
                print("正确格式: 'x,y,z x,y,z x,y,z' (位置 目标 上方向)")
        except Exception as e:
            print(f"解析相机参数时发生错误: {e}。将使用默认相机设置。")
    
    # 准备渲染配置
    render_config = {
        'integrator_type': args.get('integrator', 'path'),
        'samples_per_pixel': args.get('samples', 256),
        'max_depth': args.get('max_depth', -1),
        'film_width': args.get('resolution', [3840, 2160])[0],
        'film_height': args.get('resolution', [3840, 2160])[1],
        'fov': args.get('fov', 91.49),
        'points': transformed_points,
        'colors': point_colors,
        'point_radius': args.get('point_radius', 0.015),
        'include_ground': args.get('include_ground', True),
        'include_area_light': args.get('include_area_light', True)
    }
    
    # 添加相机配置
    render_config.update(camera_config)
    
    # 生成场景XML
    xml_content = generate_scene_xml(render_config)
    if not save_scene_xml(xml_content, xml_file):
        return False
    
    # 在CI测试模式下，创建一个空的输出文件并返回
    if ci_test_mode or mitsuba_path == "mock_mitsuba":
        print("CI测试模式: 跳过实际渲染，创建空的输出文件")
        
        # 创建一个空的或简单的输出文件
        if output_format != 'exr':
            # 创建一个简单的PNG/JPG文件
            from PIL import Image
            img = Image.new('RGB', (64, 64), color = (73, 109, 137))
            img.save(output_file)
        else:
            # 创建一个空的EXR文件 (这可能需要额外的库)
            with open(exr_file, 'wb') as f:
                f.write(b'SIMPLE_EXR_PLACEHOLDER')
                
        print(f"CI测试模式: 创建了输出文件: {output_file if output_format != 'exr' else exr_file}")
        return True
    
    # 调用Mitsuba渲染
    print(f"调用Mitsuba进行渲染: {xml_file} -> {exr_file}")
    try:
        # 不捕获标准输出，这样Mitsuba的进度条可以直接显示
        result = subprocess.run(
            [mitsuba_path, "-m", "scalar_rgb", xml_file, "-o", exr_file],
            check=True,
            stdout=None,  # 不捕获标准输出，让它直接显示在控制台
            stderr=subprocess.PIPE,
            text=True
        )
        print("Mitsuba渲染完成。")
    except subprocess.CalledProcessError as e:
        print(f"Mitsuba渲染失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"错误: 未找到Mitsuba可执行文件 '{mitsuba_path}'。")
        return False
    
    # 转换EXR为输出格式
    if output_format != 'exr':
        print(f"转换EXR为{output_format.upper()}: {exr_file} -> {output_file}")
        flip_horizontal = args.get('flip_horizontal', False)
        if not convert_exr_to_image(exr_file, output_file, flip_horizontal):
            return False
    
    # 清理中间文件
    if args.get('cleanup', False):
        if output_format != 'exr':
            print(f"清理中间EXR文件: {exr_file}")
            os.remove(exr_file)
        print(f"清理中间XML文件: {xml_file}")
        os.remove(xml_file)
    
    print(f"渲染完成，输出文件: {output_file if output_format != 'exr' else exr_file}")
    return True

def batch_render(input_files, output_dir, config):
    """
    批量渲染多个点云文件
    
    参数:
        input_files (list): 输入点云文件路径列表
        output_dir (str): 输出目录
        config (dict): 渲染配置参数
    
    返回:
        tuple: (成功数, 总数)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    success_count = 0
    total_count = len(input_files)
    
    for i, input_file in enumerate(input_files):
        print(f"\n[{i+1}/{total_count}] 渲染: {input_file}")
        
        # 为每个文件创建配置副本
        file_config = config.copy()
        file_config['input_file'] = input_file
        file_config['output_dir'] = output_dir
        
        # 如果没有指定输出前缀，使用文件名
        if 'output_prefix' not in file_config:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            file_config['output_prefix'] = base_name
        
        # 渲染点云
        if render_point_cloud(file_config):
            success_count += 1
    
    print(f"\n批量渲染完成。成功: {success_count}/{total_count}")
    return success_count, total_count 