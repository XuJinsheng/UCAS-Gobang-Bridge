#include <stdio.h>
#include <string.h>
char s[100];
int main()
{
	//setbuf(stdout, NULL);
	int row=7,col=7;
    puts("READY\n");
	fflush(stdout);
	gets(s);
	if(strcmp(s,"BLACK")==0)
		printf("MOVE(1,1)\n");
	fflush(stdout);
    while(1){
		scanf(" MOVE(%d,%d)",&row,&col);
		printf("MOVE(%d,%d)\n",row,col>14?1:col+1);
	fflush(stdout);
	}
    return 0;
}