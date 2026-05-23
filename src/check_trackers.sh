#!/bin/bash
# 快速检查 libsurvive_ros2 tracker 信息的脚本

echo "=== 检查 libsurvive_ros2 tracker 信息 ==="
echo ""

# 检查 /tf 和 /tf_static 话题是否存在，并且至少有一个有发布者
# 使用 --no-daemon，避免 ROS 2 daemon 缓存导致刚启动时误判为没有发布者
TF_INFO=$(ros2 topic info --no-daemon /tf 2>/dev/null)
TF_STATIC_INFO=$(ros2 topic info --no-daemon /tf_static 2>/dev/null)

HAS_TF_PUB=0
HAS_TF_STATIC_PUB=0

if echo "$TF_INFO" | grep -q "Publisher count: [1-9]"; then
    HAS_TF_PUB=1
fi

if echo "$TF_STATIC_INFO" | grep -q "Publisher count: [1-9]"; then
    HAS_TF_STATIC_PUB=1
fi

if [ "$HAS_TF_PUB" -eq 0 ] && [ "$HAS_TF_STATIC_PUB" -eq 0 ]; then
    echo "❌ libsurvive_ros2 未运行，或 /tf 与 /tf_static 都没有发布者"
    echo ""
    echo "请先启动 libsurvive_ros2:"
    echo "  终端 1: source /opt/ros/jazzy/setup.bash"
    echo "         source /home/lzq/ros2_ws/install/setup.bash"
    echo "         ros2 launch libsurvive_ros2 libsurvive_ros2.launch.py"
    echo ""
    exit 1
fi

echo "✅ libsurvive_ros2 正在运行"
echo "   /tf 发布者: ${HAS_TF_PUB}"
echo "   /tf_static 发布者: ${HAS_TF_STATIC_PUB}"
echo ""

# 获取 TF 数据
echo "正在获取 tracker / 基站列表（等待最多 10 秒）..."
echo ""

# 监听 /tf 话题，收集多条消息以捕获所有动态 tracker
rm -f /tmp/tf_data.txt /tmp/tf_static_data.txt

if [ "$HAS_TF_PUB" -eq 1 ]; then
    timeout 10 ros2 topic echo --no-daemon /tf > /tmp/tf_data.txt 2>&1 &
    ECHO_PID=$!
    sleep 8
    kill $ECHO_PID 2>/dev/null
    wait $ECHO_PID 2>/dev/null
fi

# 监听 /tf_static 话题，静态基站通常发布在这里，需要 transient_local 才能收到已发布消息
if [ "$HAS_TF_STATIC_PUB" -eq 1 ]; then
    ros2 topic echo --no-daemon /tf_static --qos-durability transient_local --once --timeout 3 \
        > /tmp/tf_static_data.txt 2>&1
fi

# 提取所有唯一的 child_frame_id
DYNAMIC_FRAMES=$(grep "child_frame_id:" /tmp/tf_data.txt 2>/dev/null | sed 's/.*child_frame_id: //' | sort -u)
STATIC_FRAMES=$(grep "child_frame_id:" /tmp/tf_static_data.txt 2>/dev/null | sed 's/.*child_frame_id: //' | sort -u)

echo "检测到的设备:"
echo "===================="

if [ -n "$STATIC_FRAMES" ]; then
    echo "[基站 / 静态帧 /tf_static]"
    echo "$STATIC_FRAMES"
    echo ""
fi

if [ -n "$DYNAMIC_FRAMES" ]; then
    echo "[Tracker / 动态帧 /tf]"
    echo "$DYNAMIC_FRAMES"
    echo ""
fi

if [ -z "$STATIC_FRAMES" ] && [ -z "$DYNAMIC_FRAMES" ]; then
    echo "⚠️  未检测到任何 tracker 或基站"
    echo ""
    echo "可能的原因："
    echo "  1. Tracker 未开机或未在基站视野范围内"
    echo "  2. 基站未正常工作，或 /tf_static 没有成功发布"
    echo "  3. libsurvive 仍在初始化（可以再次运行此脚本）"
    echo "  4. USB 设备权限问题（检查 /dev/hidraw* 是否有可访问设备）"
fi

echo ""
echo "===================="
echo ""
echo "设备类型说明:"
echo "  - LHR-XXXXXXXX = Vive Tracker (追踪器)"
echo "  - LHB-XXXXXXXX = Lighthouse Base station (基站)"
echo ""
echo "请记录你的 tracker 名称（LHR-开头），稍后配置时需要用到。"
echo ""
