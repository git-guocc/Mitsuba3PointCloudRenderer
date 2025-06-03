#!/usr/bin/env python
"""
Mitsuba2 点云渲染工具

使用Mitsuba2渲染引擎渲染点云文件。
"""

import argparse
import os
import sys
import glob
from mitsuba_pcr.render import render_point_cloud, batch_render

def main():
    parser = argparse.ArgumentParser(description="使用Mitsuba2渲染点云")
    
    # 输入/输出参数
    parser.add_argument("input_file", help="输入点云文件路径 (.ply, .npy, .npz)，或包含多个文件的目录")
    parser.add_argument("--output_dir", default=".", help="输出目录")
    parser.add_argument("--output_prefix", help="输出文件前缀")
    parser.add_argument("--output_format", choices=["png", "jpg", "exr"], default="png", help="输出图像格式")
    parser.add_argument("--batch", action="store_true", help="批量处理模式，输入可以是目录或通配符模式")
    parser.add_argument("--pattern", default="*.ply", help="批量模式下的文件匹配模式 (默认: '*.ply')")
    
    # 渲染参数
    parser.add_argument("--integrator", choices=["path", "direct"], default="direct", 
                        help="Mitsuba积分器类型: path (完整光照和阴影), direct (简化光照)")
    parser.add_argument("--samples", type=int, default=256, help="每像素采样数")
    parser.add_argument("--max_depth", type=int, default=-1, help="最大光线深度 (-1表示无限)")
    parser.add_argument("--num_points", type=int, default=50000, help="渲染点数 (-1表示使用原始点云的全部点数)")
    parser.add_argument("--point_radius", type=float, default=0.006, help="点半径")
    parser.add_argument("--resolution", nargs=2, type=int, default=[3840, 2160], help="输出分辨率 (宽 高)")
    
    # 颜色参数
    parser.add_argument("--color_mode", choices=["original", "position", "height", "fixed"], default="original", 
                        help="颜色模式: original (使用点云原始颜色), position (基于位置), height (基于高度), fixed (固定颜色)")
    parser.add_argument("--fixed_color", nargs=3, type=float, default=[0.7, 0.7, 0.7], 
                        help="固定颜色 (R G B)，当color_mode为'fixed'时使用")
    parser.add_argument("--color_axis", type=int, choices=[0, 1, 2], default=2, 
                        help="用于'height'颜色模式的坐标轴 (0=X, 1=Y, 2=Z)")
    parser.add_argument("--color_map", choices=["viridis", "jet", "rainbow", "turbo"], default="viridis", 
                        help="用于'height'颜色模式的颜色映射")
    
    # 相机参数
    parser.add_argument("--camera_params", 
                        default="0.09770605035067784,-0.29006978912070797,-1.029326500758792 "
                                "0.025620007887482643,0.0030496367253363132,0.01684780353680253 "
                                "-0.9927382790595731,0.05145597206648632,-0.10873358371970461",
                        help="相机参数: 'origin_x,origin_y,origin_z target_x,target_y,target_z up_x,up_y,up_z'")
    parser.add_argument("--fov", type=float, default=91.49, help="视场角（度）")
    
    # 图像翻转参数（默认翻转）
    flip_group = parser.add_mutually_exclusive_group()
    flip_group.add_argument("--flip_horizontal", dest="flip_horizontal", action="store_true", 
                        help="水平翻转输出图像（默认）")
    flip_group.add_argument("--no_flip_horizontal", dest="flip_horizontal", action="store_false", 
                        help="不水平翻转输出图像")
    parser.set_defaults(flip_horizontal=True)
    
    # 场景参数
    parser.add_argument("--include_ground", action="store_true", default=True, help="包含地面平面")
    parser.add_argument("--no_ground", dest="include_ground", action="store_false", help="不包含地面平面")
    parser.add_argument("--include_area_light", action="store_true", default=True, help="包含面光源")
    parser.add_argument("--no_area_light", dest="include_area_light", action="store_false", help="不包含面光源")
    
    # 其他参数
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--cleanup", action="store_true", help="清理中间文件（XML和EXR）")
    parser.add_argument("--mitsuba_path", help="Mitsuba可执行文件路径")
    
    args = parser.parse_args()
    
    # 批量处理模式
    if args.batch:
        input_files = []
        input_path = args.input_file
        
        if os.path.isdir(input_path):
            # 如果输入是目录，使用pattern匹配文件
            pattern = os.path.join(input_path, args.pattern)
            input_files = glob.glob(pattern)
        else:
            # 否则，将输入视为glob模式
            input_files = glob.glob(input_path)
        
        if not input_files:
            print(f"错误: 未找到匹配的文件: {args.input_file} (模式: {args.pattern})")
            return 1
        
        print(f"找到 {len(input_files)} 个文件进行批量渲染。")
        success_count, total_count = batch_render(input_files, args.output_dir, vars(args))
        
        if success_count == total_count:
            return 0
        else:
            return 1
    else:
        # 单文件处理模式
        if not os.path.exists(args.input_file):
            print(f"错误: 输入文件不存在: {args.input_file}")
            return 1
        
        success = render_point_cloud(args)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 