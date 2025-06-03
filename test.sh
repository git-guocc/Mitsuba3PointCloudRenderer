#!/usr/bin/env bash
set -e

# 渲染一帧图片（不需要交互）
python render_point_cloud.py examples\data\pcl\HelloKitty.ply --output_dir test_output --samples 8

# 生成转盘GIF（低分辨率快速测试）
python tools/create_turntable_gif.py examples\data\pcl\HelloKitty.ply --output_gif test_output\HelloKitty_turntable.gif --frames 4 --samples 4 --resolution 320 240

# 检查输出文件是否存在
if [ ! -f test_output\HelloKitty_turntable.gif ]; then
  echo "转盘GIF未生成，测试失败"
  exit 1
fi

echo "CI测试通过"

