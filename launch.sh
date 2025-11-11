#!/bin/bash
# launch-subshell.sh - 使用子shell实现环境隔离

# 检查虚拟环境和脚本是否存在
[ ! -f "venv/bin/activate" ] && { echo "错误：未找到venv虚拟环境" >&2; exit 1; }
[ ! -f "get-text.py" ] && { echo "错误：未找到get-text.py脚本" >&2; exit 1; }

# 在子shell中执行（自动继承当前环境但退出后恢复）
(
    source venv/bin/activate || exit 1
    echo "虚拟环境已激活（PID $$）"
    python get-text.py "$@"
    # 子shell退出时自动deactivate
)
# 此处已自动退出虚拟环境

# 检查子shell执行状态
if [ $? -ne 0 ]; then
    echo "执行失败" >&2
    exit 1
fi

echo "执行完成"
exit 0
