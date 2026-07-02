import 'package:flutter/material.dart';

import 'router.dart';
import 'theme.dart';

class BapMukJaApp extends StatelessWidget {
  const BapMukJaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'PNU 밥묵자',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      routerConfig: appRouter,
    );
  }
}
