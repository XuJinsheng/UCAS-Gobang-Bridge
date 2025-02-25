#include <stdio.h>
#include <string.h>
char s[100];
int main()
{
	puts("READY\n");			 // 输出READY表示初始化完成
	fflush(stdout);				 // puts和printf之后都要刷新缓冲区
	gets(s);					 // 读取自己的颜色
	if (strcmp(s, "BLACK") == 0) // 判断自己是黑方还是白方
		printf("MOVE H8\n");	 // 如果是黑方，就先下一步
	fflush(stdout);
	while (1)
	{
		int row = 7, col = 7;char c;
		// 读取对手下棋的坐标，注意scanf的空格很重要，不然会读到换行符等
		scanf(" MOVE %c%d", &c, &row);
		col = c - 'A' + 1;

		// 然后根据对手的坐标下一步棋，这里只是简单的下在对手的右边
		row = row;
		col = col > 14 ? 1 : col + 1;

		// 输出自己的下棋坐标
		// printf("MOVE %d %d\n", row, col);
		printf("MOVE %c%d\n", col + 'A' - 1, row);
		fflush(stdout);
	}
	return 0;
}