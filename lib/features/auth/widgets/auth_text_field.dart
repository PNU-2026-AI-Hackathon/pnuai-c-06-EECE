import 'package:flutter/material.dart';

import '../../../app/theme.dart';

/// 로그인/회원가입 공용 입력 필드 — 실서비스(네이버 등) 로그인 UX 모방:
/// · 포커스 시 파란 테두리 + 라벨/아이콘 색 전환 (커서 깜빡임은 기본 제공)
/// · 입력 중 지우기(X) 버튼
/// · 비밀번호 표시/숨김 토글
class AuthTextField extends StatefulWidget {
  const AuthTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.icon,
    this.obscure = false,
    this.keyboardType,
    this.textInputAction,
    this.onSubmitted,
    this.errorText,
    this.autofillHints,
    this.enabled = true,
    this.focusNode,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final IconData? icon;
  final bool obscure;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final ValueChanged<String>? onSubmitted;
  final String? errorText;
  final Iterable<String>? autofillHints;
  final bool enabled;

  /// 외부에서 포커스 제어가 필요할 때 주입 (예: 이메일 → 비밀번호 이동)
  final FocusNode? focusNode;

  @override
  State<AuthTextField> createState() => _AuthTextFieldState();
}

class _AuthTextFieldState extends State<AuthTextField> {
  late final FocusNode _focusNode = widget.focusNode ?? FocusNode();
  bool _focused = false;
  bool _showPassword = false;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _hasText = widget.controller.text.isNotEmpty;
    _focusNode.addListener(_onFocusChanged);
    widget.controller.addListener(_onTextChanged);
  }

  void _onFocusChanged() => setState(() => _focused = _focusNode.hasFocus);

  void _onTextChanged() {
    final has = widget.controller.text.isNotEmpty;
    if (has != _hasText) setState(() => _hasText = has);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    _focusNode.removeListener(_onFocusChanged);
    // 외부에서 주입한 FocusNode는 주입한 쪽에서 dispose
    if (widget.focusNode == null) _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasError = widget.errorText != null;
    final activeColor = hasError ? AppColors.crowded : AppColors.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 포커스 시 배경·테두리가 함께 변하는 컨테이너 (부드러운 전환)
        AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          decoration: BoxDecoration(
            color: _focused ? Colors.white : const Color(0xFFF7F9FC),
            borderRadius: BorderRadius.circular(kRadiusButton),
            border: Border.all(
              color: hasError
                  ? AppColors.crowded
                  : _focused
                      ? AppColors.primary
                      : const Color(0xFFDDE4EE),
              width: _focused || hasError ? 1.8 : 1.2,
            ),
            boxShadow: _focused
                ? [
                    BoxShadow(
                      color: activeColor.withValues(alpha: 0.12),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: TextField(
            controller: widget.controller,
            focusNode: _focusNode,
            enabled: widget.enabled,
            obscureText: widget.obscure && !_showPassword,
            keyboardType: widget.keyboardType,
            textInputAction: widget.textInputAction,
            onSubmitted: widget.onSubmitted,
            autofillHints: widget.autofillHints,
            cursorColor: AppColors.primary,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: AppColors.textStrong,
            ),
            decoration: InputDecoration(
              labelText: widget.label,
              hintText: widget.hint,
              labelStyle: TextStyle(
                fontSize: 14,
                color: _focused ? activeColor : AppColors.textWeak,
                fontWeight: _focused ? FontWeight.w700 : FontWeight.w500,
              ),
              hintStyle: const TextStyle(
                fontSize: 14,
                color: Color(0xFFB4BCCA),
              ),
              prefixIcon: widget.icon == null
                  ? null
                  : Icon(
                      widget.icon,
                      size: 20,
                      color: _focused ? activeColor : AppColors.textWeak,
                    ),
              suffixIcon: _buildSuffix(),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
            ),
          ),
        ),
        // 인라인 에러 (필드 바로 아래)
        if (hasError)
          Padding(
            padding: const EdgeInsets.only(top: 6, left: 4),
            child: Row(
              children: [
                const Icon(
                  Icons.error_outline,
                  size: 14,
                  color: AppColors.crowded,
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    widget.errorText!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.crowded,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  /// 지우기(X) + 비밀번호 표시 토글
  Widget? _buildSuffix() {
    final children = <Widget>[
      if (_hasText && _focused)
        IconButton(
          // 키보드 탭 이동 시 버튼이 포커스를 가로채지 않게
          focusNode: FocusNode(skipTraversal: true),
          icon: const Icon(Icons.cancel, size: 18, color: Color(0xFFB4BCCA)),
          onPressed: () => widget.controller.clear(),
          tooltip: '지우기',
        ),
      if (widget.obscure)
        IconButton(
          focusNode: FocusNode(skipTraversal: true),
          icon: Icon(
            _showPassword
                ? Icons.visibility_outlined
                : Icons.visibility_off_outlined,
            size: 20,
            color: _showPassword ? AppColors.primary : AppColors.textWeak,
          ),
          onPressed: () => setState(() => _showPassword = !_showPassword),
          tooltip: _showPassword ? '비밀번호 숨기기' : '비밀번호 표시',
        ),
    ];
    if (children.isEmpty) return null;
    return Row(mainAxisSize: MainAxisSize.min, children: children);
  }
}
